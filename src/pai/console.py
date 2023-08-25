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
        super().showtraceback(*args, **kwargs)


class Console:
    console: CustomInteractiveConsole
    history_tree: HistoryTree
    llm: LLM

    def __init__(self, llm: LLM):
        self.console = CustomInteractiveConsole()
        self.history_tree = HistoryTree()
        self.llm = llm

    def is_expression(self, code: str) -> bool:
        """Check if the given code is an expression."""
        try:
            ast.parse(code, mode="eval")
            return True
        except:
            return False

    def push_line(self, source: str) -> str:
        """Push a line of code to the Console. Return a tuple of (more_input_required, output)"""
        collector = io.StringIO()
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        sys.stdout = collector
        sys.stderr = collector

        all_lines = source.strip().split("\n")
        last_line = all_lines[-1]

        # If the last line of the full_code is an expression, evaluate it after executing the rest
        if self.is_expression(last_line):
            # Execute all lines except the last one
            exec_code = "\n".join(all_lines[:-1])
            try:
                compiled_code = compile(exec_code, "<string>", "exec")
                self.console.runcode(compiled_code)

                # if there was not exception, then we can evaluate the last line
                if not self.console.last_exception:
                    self.console.push(last_line)
            except Exception as e:
                # handle an error compiling the exec_code
                sys.stdout = original_stdout
                sys.stderr = original_stderr
                return f"{e}"
        else:
            # If the last line is not an expression, try to compile and execute the full_code
            try:
                compiled_code = compile(source, "<string>", "exec")
                self.console.runcode(compiled_code)
            except SyntaxError as e:
                sys.stdout = original_stdout
                sys.stderr = original_stderr
                return f"{e}\n"

        # clear the last exception
        self.console.last_exception = None

        # restore stdout and stderr
        sys.stdout = original_stdout
        sys.stderr = original_stderr

        # get the output from the collector
        output = collector.getvalue()
        return output

    def handle_line(self, line: ConsoleInput) -> Optional[str]:
        if isinstance(line, (UserInput, LLMCodeInput)):
            # check if the line is empty
            if line.code.strip() == "":
                return None

            # push the line to the console
            out = self.push_line(line.code)

            # add the new node to the history tree
            if isinstance(line, UserInput):
                self.history_tree.add_node(
                    HistoryNode.UserCode(code=line.code, result=out)
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
            out = append_new_line(line.message)
            return out
        elif isinstance(line, LLMErrorInput):
            self.history_tree.add_node(
                HistoryNode.LLMError(
                    prompt=line.prompt, error=line.error, raw_resp=line.raw_resp
                )
            )
            out = append_new_line(line.error)
            return out

    def gen_code(self, prompt: str) -> LLMResponse:
        """Generate code using the LLM."""
        return self.llm.call(self.history_tree.lineage(), prompt)


def append_new_line(text: str) -> str:
    """Append a new line to the end of the string if it doesn't already have one."""
    if text[-1] != "\n":
        text += "\n"
    return text
