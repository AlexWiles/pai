from typing import Any, Generator, List, Optional, Union
from pydantic.dataclasses import dataclass
from pai.code_exec import CodeExec

from pai.history import HistoryNode, HistoryTree
from pai.llms.llm_protocol import (
    LLM,
    LLMError,
    LLMResponseCode,
    LLMResponseMessage,
    LLMStreamChunk,
)


@dataclass
class UserCode:
    code: str
    name: str = "user-code"


@dataclass
class LLMCode:
    prompt: str
    message: Optional[str]
    code: str
    raw_resp: Any
    agent_mode: bool = False
    name: str = "llm-code"


ConsoleInput = Union[UserCode, LLMCode]


@dataclass
class WaitingForInput:
    """Waiting for input from the user."""

    name: str = "waiting-for-input"


@dataclass
class WaitingForInputApproval:
    """Approve the given code."""

    code: LLMCode
    name: str = "waiting-for-input-approval"


@dataclass
class WaitingForLLM:
    """Waiting for the LLM to return a response."""

    name: str = "waiting-for-llm"


@dataclass
class LLMMessage:
    """A new message from the LLM."""

    value: str
    name: str = "llm-message"


@dataclass
class CodeResult:
    """A new output from code execution."""

    value: str
    name: str = "code-result"


ConsoleEvent = Union[
    WaitingForInput,
    WaitingForInputApproval,
    WaitingForLLM,
    CodeResult,
    LLMMessage,
    LLMStreamChunk,
]


class PaiConsole:
    "Manages the state of the console."
    console: CodeExec
    history_tree: HistoryTree
    llm: LLM
    max_history_nodes_for_llm_context: Optional[int]

    def __init__(self, llm: LLM, llm_context_nodes: Optional[int] = None, locals={}):
        self.console = CodeExec(locals=locals)
        self.history_tree = HistoryTree()
        self.llm = llm
        self.max_history_nodes_for_llm_context = llm_context_nodes

    def code_gen(
        self, prompt: str, agent_mode: bool = False
    ) -> Union[LLMCode, LLMMessage]:
        # get the events from the code gen
        events = [e for e in self.streaming_code_gen(prompt, agent_mode=agent_mode)]

        # if the last event is a code input, then return it
        if isinstance(events[-1], WaitingForInputApproval):
            return events[-1].code

        # if the last message is a waiting for input, then return the second to last event
        # verify the second to last event is a message
        if isinstance(events[-1], WaitingForInput) and isinstance(
            events[-2], LLMMessage
        ):
            return events[-2]

        raise ValueError(
            f"Unexpected state. Second to last event should be a message but got {events[-2]}"
        )

    def streaming_code_gen(
        self, prompt: str, agent_mode: bool = False
    ) -> Generator[ConsoleEvent, None, None]:
        """
        Handles code gen commands. calls the llm, sets correct input state, updates the history

        prompt: the prompt to use for the llm

        agent_mode: sets the agent_mode flag on LLMCodeInput (if returned) so when it is
        later passed to handle_input, it will call the llm again immediately

        """
        # set the input state to waiting for the LLM and yield it
        yield WaitingForLLM()

        history = self.history_tree.lineage(
            max_nodes=self.max_history_nodes_for_llm_context
        )
        resp = yield from self.llm.call(history, prompt)

        if isinstance(resp, LLMResponseCode):
            llm_inp = LLMCode(
                prompt=resp.prompt,
                message=resp.message,
                code=resp.code,
                raw_resp=resp.raw,
                agent_mode=agent_mode,
            )
            # yield the message if there is one
            if resp.message:
                yield LLMMessage(resp.message)
            # yield the code input
            yield WaitingForInputApproval(llm_inp)
        elif isinstance(resp, LLMResponseMessage):
            new_history_node = HistoryNode.LLMMessage(
                prompt=resp.prompt,
                message=resp.message,
                raw_resp=resp.raw,
            )
            yield LLMMessage(value=resp.message)
            self.history_tree.add_node(new_history_node)
            yield WaitingForInput()
        elif isinstance(resp, LLMError):
            new_history_node = HistoryNode.LLMError(
                prompt=resp.prompt,
                error=resp.error,
                raw_resp=resp.raw,
            )
            yield LLMMessage(resp.error)
            self.history_tree.add_node(new_history_node)
            yield WaitingForInput()
        else:
            raise ValueError(f"Unknown LLM response type: {type(resp)}")

    def exec(self, console_input: Union[ConsoleInput, str]):
        last_event = None

        # if the input is a string, then convert it to a UserInput
        if isinstance(console_input, str):
            console_input = UserCode(code=console_input)

        for event in self.streaming_exec(console_input):
            if isinstance(event, WaitingForInput):
                return last_event
            last_event = event

    def streaming_exec(
        self, console_input: ConsoleInput
    ) -> Generator[ConsoleEvent, None, None]:
        """
        Yields console events.
        Returns the next input state.

        There maybe multiple console events that are yielded before the next input state is returned.
        The caller can use the events to update the UI in realtime.
        The next input state describes what sort of input to collect next.
        """

        if isinstance(console_input, UserCode):
            if console_input.code.strip() == "":
                yield WaitingForInput()
            # if the input is not a special command, then run it
            result = self.console.custom_run_source(console_input.code)
            yield CodeResult(result)
            self.history_tree.add_node(
                HistoryNode.UserCode(code=console_input.code, result=result)
            )
            yield WaitingForInput()
        elif isinstance(console_input, LLMCode):
            result = self.console.custom_run_source(console_input.code)
            yield CodeResult(result)

            new_history_node = HistoryNode.LLMCode(
                prompt=console_input.prompt,
                code=console_input.code,
                result=result,
                raw_resp=console_input.raw_resp,
            )
            self.history_tree.add_node(new_history_node)

            if console_input.agent_mode:
                # if agent mode is enabled, then we want to immediately call the LLM again
                # and it will generate code based on the result of the previous code
                yield from self.streaming_code_gen("", agent_mode=True)
            else:
                # otherwise, just return to waiting for input
                yield WaitingForInput()
        else:
            raise ValueError(f"Unknown input type: {type(console_input)}")

    def get_history(self) -> List[HistoryNode]:
        """Get the history of the console."""
        return self.history_tree.lineage(self.max_history_nodes_for_llm_context)

    def get_history_since(self, idx: int) -> List[HistoryNode]:
        return self.history_tree.lineage_since(idx)

    def get_prompt(self, prompt: str) -> Any:
        """Get the prompt for the LLM"""
        return self.llm.prompt(self.get_history(), prompt)

    def initial_state_generator(self) -> Generator[ConsoleEvent, None, None]:
        # yield the initial waiting for input state
        yield WaitingForInput()


def append_new_line(text: str) -> str:
    """Append a new line to the end of the string if it doesn't already have one."""
    if text[-1] != "\n":
        text += "\n"
    return text
