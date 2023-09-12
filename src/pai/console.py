from typing import Any, Generator, Optional
from pydantic.dataclasses import dataclass
from pai.code_exec import CodeExec

from pai.history import HistoryNode, HistoryTree
from pai.llms.llm_protocol import (
    LLM,
    LLMError,
    LLMResponse,
    LLMResponseCode,
    LLMResponseMessage,
    LLMStreamChunk,
)


@dataclass
class UserInput:
    code: str


@dataclass
class LLMCodeInput:
    prompt: str
    message: Optional[str]
    code: str
    raw_resp: Any
    agent_mode: bool = False


@dataclass
class LLMMessageInput:
    prompt: str
    message: str
    raw_resp: Any


@dataclass
class LLMErrorInput:
    prompt: str
    error: str
    raw_resp: Any


ConsoleInput = UserInput | LLMCodeInput | LLMMessageInput | LLMErrorInput


@dataclass
class WaitingForInput:
    """Waiting for input from the user."""

    pass


@dataclass
class WaitingForInputApproval:
    """Approve the given code."""

    code: LLMCodeInput


@dataclass
class WaitingForLLM:
    """Waiting for the LLM to return a response."""

    pass


@dataclass
class NewLLMMessage:
    """A new message from the LLM."""

    value: str


@dataclass
class NewCodeOuput:
    """A new output from code execution."""

    value: str


ConsoleEvent = (
    WaitingForInput
    | WaitingForInputApproval
    | WaitingForLLM
    | NewCodeOuput
    | NewLLMMessage
    | LLMStreamChunk
)


class Console:
    "Manages the state of the console."
    console: CodeExec
    history_tree: HistoryTree
    llm: LLM
    max_history_nodes_for_llm_context: Optional[int]

    input_state: WaitingForInput | WaitingForInputApproval

    def __init__(self, llm: LLM, llm_context_nodes: Optional[int] = None):
        self.history_tree = HistoryTree()
        self.llm = llm
        self.max_history_nodes_for_llm_context = llm_context_nodes

        # holds input that is not yet processed. This is used for generated code.
        self.input_state = WaitingForInput()

        locals = {"history": self.history_tree}
        self.console = CodeExec(locals=locals)

    def code_gen(
        self, prompt: str, start_agent: bool = False
    ) -> Generator[ConsoleEvent, None, None]:
        "Handles code gen commands. calls the llm, sets correct input state, updates the history"
        # set the input state to waiting for the LLM and yield it
        yield WaitingForLLM()

        history = self.history_tree.lineage(
            max_nodes=self.max_history_nodes_for_llm_context
        )
        resp = yield from self.llm.call(history, prompt)

        if isinstance(resp, LLMResponseCode):
            llm_inp = LLMCodeInput(
                prompt=resp.prompt,
                message=resp.message,
                code=resp.code,
                raw_resp=resp.raw,
            )
            if resp.message:
                yield NewLLMMessage(resp.message)

            next_state = WaitingForInputApproval(llm_inp)
            if start_agent:
                # if agent mode is enabled, that means that we want to immediately
                # call the LLM again with the result of the previous code
                next_state.code.agent_mode = True
            yield next_state
        elif isinstance(resp, LLMResponseMessage):
            new_history_node = HistoryNode.LLMMessage(
                prompt=resp.prompt,
                message=resp.message,
                raw_resp=resp.raw,
            )
            yield NewLLMMessage(value=resp.message)
            self.history_tree.add_node(new_history_node)
        elif isinstance(resp, LLMError):
            new_history_node = HistoryNode.LLMError(
                prompt=resp.prompt,
                error=resp.error,
                raw_resp=resp.raw,
            )
            yield NewLLMMessage(resp.error)
            self.history_tree.add_node(new_history_node)
        else:
            raise ValueError(f"Unknown LLM response type: {type(resp)}")

        yield WaitingForInput()

    def handle_input(
        self, console_input: ConsoleInput
    ) -> Generator[ConsoleEvent, None, None]:
        """
        Yields a console event.
        Returns the next input state.

        There maybe multiple console events that are yielded before the next input state is returned.
        The caller can use the events to update the UI in realtime.
        The next input state describes what sort of input to collect next.
        """
        # reset the input state
        self.input_state = WaitingForInput()

        if isinstance(console_input, UserInput):
            if console_input.code.strip() == "":
                yield WaitingForInput()
            # if the input is not a special command, then run it
            result = self.console.custom_run_source(console_input.code)
            yield NewCodeOuput(result)
            self.history_tree.add_node(
                HistoryNode.UserCode(code=console_input.code, result=result)
            )
            yield WaitingForInput()
        elif isinstance(console_input, LLMCodeInput):
            result = self.console.custom_run_source(console_input.code)
            yield NewCodeOuput(result)

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
                yield from self.code_gen("")
            else:
                # otherwise, just return to waiting for input
                yield WaitingForInput()
        elif isinstance(console_input, LLMMessageInput):
            new_history_node = HistoryNode.LLMMessage(
                prompt=console_input.prompt,
                message=console_input.message,
                raw_resp=console_input.raw_resp,
            )
            self.history_tree.add_node(new_history_node)
            yield WaitingForInput()
        elif isinstance(console_input, LLMErrorInput):
            new_history_node = HistoryNode.LLMError(
                prompt=console_input.prompt,
                error=console_input.error,
                raw_resp=console_input.raw_resp,
            )
            self.history_tree.add_node(new_history_node)
            yield WaitingForInput()
        else:
            raise ValueError(f"Unknown input type: {type(console_input)}")

    def get_history(self) -> list[HistoryNode]:
        """Get the history of the console."""
        return self.history_tree.lineage(self.max_history_nodes_for_llm_context)

    def get_history_since(self, idx: int) -> list[HistoryNode]:
        return self.history_tree.lineage_since(idx)

    def get_prompt(self, prompt: str) -> Any:
        """Get the prompt for the LLM"""
        return self.llm.prompt(self.get_history(), prompt)

    def start_generator(self) -> Generator[ConsoleEvent, ConsoleInput, None]:
        # yield the initial waiting for input state
        yield WaitingForInput()


def append_new_line(text: str) -> str:
    """Append a new line to the end of the string if it doesn't already have one."""
    if text[-1] != "\n":
        text += "\n"
    return text
