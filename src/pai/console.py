import ast
import code
import io
import sys
from typing import Any, Optional
from pydantic.dataclasses import dataclass

from pai.history import HistoryNode, HistoryTree
from pai.llms.llm import LLM, LLMResponse


@dataclass
class UserInput:
    code: str


@dataclass
class LLMCodeInput:
    prompt: str
    message: Optional[str]
    code: str
    raw_resp: Any


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


class CustomInteractiveConsole(code.InteractiveConsole):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.last_exception = None

    def showtraceback(self, *args, **kwargs):
        """Override the default traceback behavior to store the last exception."""
        self.last_exception = sys.exc_info()[1]


class Console:
    console: CustomInteractiveConsole
    history_tree: HistoryTree
    llm: LLM
    buffered_code: list[str]
    more_input_required: bool

    def __init__(self, llm: LLM):
        self.console = CustomInteractiveConsole()
        self.history_tree = HistoryTree()
        self.llm = llm

        self.buffered_code = []
        self.more_input_required = False

    def is_expression(self, code: str) -> bool:
        """Check if the given code is an expression."""
        try:
            ast.parse(code, mode="eval")
            return True
        except:
            return False

    def push_line(self, source: str) -> tuple:
        """Push a line of code to the Console. Return a tuple of (more_input_required, output)"""
        collector = io.StringIO()
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        sys.stdout = collector
        sys.stderr = collector

        self.buffered_code.append(source)
        full_code = "\n".join(self.buffered_code)

        all_lines = full_code.strip().split("\n")
        last_line = all_lines[-1]

        # If the last line of the full_code is an expression, evaluate it after executing the rest
        if self.is_expression(last_line):
            # Execute all lines except the last one
            exec_code = "\n".join(all_lines[:-1])
            try:
                compiled_code = compile(exec_code, "<string>", "exec")
                self.console.runcode(compiled_code)
                # self.console.runsource(exec_code)
                if self.console.last_exception:
                    error_message = str(self.console.last_exception)
                    sys.stdout = original_stdout
                    sys.stderr = original_stderr
                    self.buffered_code.clear()
                    self.console.last_exception = None
                    return (False, error_message + "\n")

                # Handle the last line
                self.console.push(last_line)
                self.buffered_code.clear()
            except Exception as e:
                sys.stdout = original_stdout
                sys.stderr = original_stderr
                self.buffered_code.clear()
                return (False, str(e))
        else:
            # If the last line is not an expression, try to compile and execute the full_code
            try:
                compiled_code = compile(full_code, "<string>", "exec")
                self.console.runcode(compiled_code)
                if self.console.last_exception:
                    error_message = str(self.console.last_exception)
                    sys.stdout = original_stdout
                    sys.stderr = original_stderr
                    self.buffered_code.clear()
                    self.console.last_exception = None
                    return (False, error_message)
                self.buffered_code.clear()
            except SyntaxError as e:
                sys.stdout = original_stdout
                sys.stderr = original_stderr
                if "unexpected EOF while parsing" in str(e):
                    # Code block is not complete, more input required
                    return (True, "")
                else:
                    self.buffered_code.clear()
                    return (False, f"SyntaxError: {e}")

        sys.stdout = original_stdout
        sys.stderr = original_stderr

        output = collector.getvalue()
        return (
            False,
            output,
        )  # Since we're handling the full code including the last line, more_input_required is always False.

    def handle_line(self, line: ConsoleInput) -> Optional[str]:
        if isinstance(line, (UserInput, LLMCodeInput)):
            (self.more_input_required, out) = self.push_line(line.code)

            # Empty line means end of statement in multiline mode
            if line.code == "" and self.more_input_required:
                self.more_input_required = False

            if self.more_input_required:
                self.buffered_code.append(line.code)
                self.more_input_required = True
                return None
            else:
                code = ""
                if len(self.buffered_code) > 0:
                    code = "\n".join(self.buffered_code) + "\n"
                code += line.code
                self.buffered_code = []
                self.more_input_required = False

                if isinstance(line, UserInput):
                    self.history_tree.add_node(
                        HistoryNode.UserCode(code=code, result=out)
                    )
                else:
                    self.history_tree.add_node(
                        HistoryNode.LLMCode(
                            prompt=line.prompt,
                            code=line.code,
                            result=out,
                            raw_resp=line.raw_resp,
                        )
                    )

                return out
        elif isinstance(line, LLMMessageInput):
            self.history_tree.add_node(
                HistoryNode.LLMMessage(
                    prompt=line.prompt, message=line.message, raw_resp=line.raw_resp
                )
            )
            # add new line to the end of the message if it doesn't already have one
            return append_new_line(line.message)
        elif isinstance(line, LLMErrorInput):
            self.history_tree.add_node(
                HistoryNode.LLMError(
                    prompt=line.prompt, error=line.error, raw_resp=line.raw_resp
                )
            )

            return append_new_line(line.error)

    def gen_code(self, prompt: str) -> LLMResponse:
        """Generate code using the LLM."""
        return self.llm.call(self.history_tree.lineage(), prompt)


def append_new_line(text: str) -> str:
    """Append a new line to the end of the string if it doesn't already have one."""
    if text[-1] != "\n":
        text += "\n"
    return text
