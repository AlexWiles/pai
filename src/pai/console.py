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


class Console:
    console: code.InteractiveConsole
    history_tree: HistoryTree
    llm: LLM
    buffered_lines: list[str]
    more_input_required: bool

    def __init__(self, llm: LLM):
        self.console = code.InteractiveConsole()
        self.history_tree = HistoryTree()
        self.llm = llm

        self.buffered_lines = []
        self.more_input_required = False

    def gen_code(self, prompt: str) -> LLMResponse:
        """Generate code using the LLM."""
        return self.llm.call(self.history_tree.lineage(), prompt)

    def push_line(self, source: str) -> tuple[bool, str]:
        """Push a line of code to the Console. Return a tuple of (more_input_required, output)"""
        collector = io.StringIO()
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        sys.stdout = collector
        sys.stderr = collector

        # split the source into lines and push them one by one
        # ''.splitlines() returns [] but we still want to push an empty line so we have the or [""] part
        more_input_required = False
        for line in source.splitlines() or [""]:
            # if more input was required from the previous line and the current line doesn't start with a space, then we need to push an empty line
            if more_input_required and not line.startswith(" "):
                self.console.push("")
            more_input_required = self.console.push(line) == 1

        # Restore original stdout and stderr
        sys.stdout = original_stdout
        sys.stderr = original_stderr

        # Get the redirected stdout and stderr
        # and store them into the `output` variable
        output = collector.getvalue()
        return (more_input_required, output)

    def handle_line(self, line: ConsoleInput) -> Optional[str]:
        if isinstance(line, (UserInput, LLMCodeInput)):
            (self.more_input_required, out) = self.push_line(line.code)

            # Empty line means end of statement in multiline mode
            if line.code == "" and self.more_input_required:
                self.more_input_required = False

            if self.more_input_required:
                self.buffered_lines.append(line.code)
                self.more_input_required = True
                return None
            else:
                code = ""
                if len(self.buffered_lines) > 0:
                    code = "\n".join(self.buffered_lines) + "\n"
                code += line.code
                self.buffered_lines = []
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


def append_new_line(text: str) -> str:
    """Append a new line to the end of the string if it doesn't already have one."""
    if text[-1] != "\n":
        text += "\n"
    return text
