import ast
import code
import io
import sys
from typing import Any, Generator, Literal, Optional
from uuid import UUID
from pydantic.dataclasses import dataclass

from pai.history import HistoryNode, HistoryTree
from pai.llms.llm_protocol import (
    LLM,
    LLMError,
    LLMResponse,
    LLMResponseCode,
    LLMResponseMessage,
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


class WrappedInteractiveConsole(code.InteractiveConsole):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.last_exception = None

    def showtraceback(self, *args, **kwargs):
        """Override the default traceback behavior to store the last exception."""
        self.last_exception = sys.exc_info()[1]
        super().showtraceback(*args, **kwargs)

    def _is_expression(self, code: str) -> bool:
        """Check if the given code is an expression."""
        try:
            ast.parse(code, mode="eval")
            return True
        except:
            return False

    def custom_run_source(self, source: str) -> str:
        """
        Push a block of code and get the string output.

        This behaves like a REPL. If the last line of the code
        is an expression, it is evaluated and the result is added to the output.

        For example:
        source:
            1+1
        returns:
            "2"

        If a block of code is given, the output is printed and the last expression
        is returned.

        source:
            def add(a, b):
                print("Adding a and b")
                return a + b
            add(1, 2)
        returns:
            "Adding a and b\n3"
        """
        collector = io.StringIO()
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        sys.stdout = collector
        sys.stderr = collector

        all_lines = source.strip().split("\n")
        last_line = all_lines[-1]

        # If the last line of the full_code is an expression, evaluate it after executing the rest
        if self._is_expression(last_line):
            # Execute all lines except the last one
            exec_code = "\n".join(all_lines[:-1])
            try:
                compiled_code = compile(exec_code, "<string>", "exec")
                self.runcode(compiled_code)

                # if there was not exception, then we can evaluate the last line
                if not self.last_exception:
                    self.push(last_line)
            except Exception as e:
                # handle an error compiling the exec_code
                sys.stdout = original_stdout
                sys.stderr = original_stderr
                return f"{e}"
        else:
            # If the last line is not an expression, try to compile and execute the full_code
            try:
                compiled_code = compile(source, "<string>", "exec")
                self.runcode(compiled_code)
            except SyntaxError as e:
                sys.stdout = original_stdout
                sys.stderr = original_stderr
                return f"{e}\n"

        # clear the last exception
        self.last_exception = None

        # restore stdout and stderr
        sys.stdout = original_stdout
        sys.stderr = original_stderr

        # get the output from the collector
        output = collector.getvalue()
        return output


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
    value: str


@dataclass
class NewOuput:
    value: str


ConsoleEvent = (
    WaitingForInput | WaitingForInputApproval | WaitingForLLM | NewOuput | NewLLMMessage
)

InputState = WaitingForInput | WaitingForInputApproval


class Console:
    "Manages the state of the console."
    console: WrappedInteractiveConsole
    history_tree: HistoryTree
    llm: LLM
    max_history_nodes_for_llm_context: Optional[int]

    input_state: WaitingForInput | WaitingForInputApproval

    def __init__(self, llm: LLM, llm_context_nodes: Optional[int] = None):
        # pass functions that can be called to gen code or start the agent
        self.console = WrappedInteractiveConsole()

        self.history_tree = HistoryTree()
        self.llm = llm
        self.max_history_nodes_for_llm_context = llm_context_nodes

        # holds input that is not yet processed. This is used for generated code.
        self.input_state = WaitingForInput()
        self.agent_mode = False

    def _code_gen(self, prompt: str) -> Generator[ConsoleEvent, None, InputState]:
        "Handles code gen commands. calls the llm, sets correct input state, updates the history"
        # set the input state to waiting for the LLM and yield it
        yield WaitingForLLM()

        history = self.history_tree.lineage(
            max_nodes=self.max_history_nodes_for_llm_context
        )
        resp = self.llm.call(history, prompt)

        if isinstance(resp, LLMResponseCode):
            llm_inp = LLMCodeInput(
                prompt=resp.prompt,
                message=resp.message,
                code=resp.code,
                raw_resp=resp.raw,
            )
            if resp.message:
                yield NewLLMMessage(resp.message)

            return WaitingForInputApproval(llm_inp)
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

        return WaitingForInput()

    def handle_input(
        self, console_input: ConsoleInput
    ) -> Generator[ConsoleEvent, None, InputState]:
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
                return WaitingForInput()

            if console_input.code.startswith("gen:"):
                prompt = console_input.code[4:].strip()
                next_input_state = yield from self._code_gen(prompt)
                return next_input_state
            elif console_input.code.startswith("pai:"):
                prompt = console_input.code[4:].strip()
                next_input_state = yield from self._code_gen(prompt)
                if isinstance(next_input_state, WaitingForInputApproval):
                    # this is the agent command
                    # so enable agent mode in the llm code input
                    # that way when it is passed back to this method
                    # we can immediately call the llm again after running the code
                    next_input_state.code.agent_mode = True
                return next_input_state
            else:
                # if the input is not a special command, then run it
                result = self.console.custom_run_source(console_input.code)
                yield NewOuput(result)
                self.history_tree.add_node(
                    HistoryNode.UserCode(code=console_input.code, result=result)
                )
                return WaitingForInput()
        elif isinstance(console_input, LLMCodeInput):
            result = self.console.custom_run_source(console_input.code)
            yield NewOuput(result)

            new_history_node = HistoryNode.LLMCode(
                prompt=console_input.prompt,
                code=console_input.code,
                result=result,
                raw_resp=console_input.raw_resp,
            )
            self.history_tree.add_node(new_history_node)

            if console_input.agent_mode:
                # if agent mode is enabled, that means that we want to immediately
                # call the LLM again with the result of the previous code
                next_input_state = yield from self._code_gen("")
                if isinstance(next_input_state, WaitingForInputApproval):
                    # TODO: this happens in two places, so it could be refactored
                    # this is the agent command
                    # so enable agent mode in the llm code input
                    # that way when it is passed back to this method
                    # we can immediately call the llm again after running the code
                    next_input_state.code.agent_mode = True
                return next_input_state
            else:
                # otherwise, just return to waiting for input
                return WaitingForInput()
        elif isinstance(console_input, LLMMessageInput):
            new_history_node = HistoryNode.LLMMessage(
                prompt=console_input.prompt,
                message=console_input.message,
                raw_resp=console_input.raw_resp,
            )
            self.history_tree.add_node(new_history_node)
            return WaitingForInput()
        elif isinstance(console_input, LLMErrorInput):
            new_history_node = HistoryNode.LLMError(
                prompt=console_input.prompt,
                error=console_input.error,
                raw_resp=console_input.raw_resp,
            )
            self.history_tree.add_node(new_history_node)
            return WaitingForInput()
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
        input_state = WaitingForInput()
        while True:
            user_input: ConsoleInput = yield input_state
            input_state = yield from self.handle_input(user_input)


def append_new_line(text: str) -> str:
    """Append a new line to the end of the string if it doesn't already have one."""
    if text[-1] != "\n":
        text += "\n"
    return text
