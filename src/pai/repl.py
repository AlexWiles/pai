from typing import Generator

from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys

from pai.console import (
    Console,
    ConsoleInput,
    LLMCodeInput,
    LLMErrorInput,
    LLMMessageInput,
    UserInput,
)
from pai.llms.llm import LLMError, LLMResponseCode, LLMResponseMessage


# Create a session object
key_bindings = KeyBindings()


@key_bindings.add(Keys.Tab)
def _(event):
    "Insert four spaces for tab key."
    event.cli.current_buffer.insert_text("    ")


@key_bindings.add("c-m")
def _(event):
    event.current_buffer.insert_text("\n")


@key_bindings.add("enter")
def _(event):
    event.current_buffer.validate_and_handle()


class REPL:
    console: Console
    session: PromptSession
    multiline: bool
    buffered_lines: list[str]

    def __init__(self, console: Console):
        self.console = console
        self.session = PromptSession(key_bindings=key_bindings)
        self.multiline = False
        self.buffered_lines = []

    def input_generator(
        self,
    ) -> Generator[ConsoleInput, None, None]:
        while True:
            prompt = "... " if self.console.more_input_required else f">>> "

            # get the next line from the user
            line: str = self.session.prompt(
                prompt,
            )

            # handle the please command
            if line.startswith("ai:"):
                line = line[3:]  # remove the "please " prefix
                resp = self.console.gen_code(line)  # generate code

                if isinstance(resp, LLMResponseCode):
                    # print the message of the response
                    if resp.message:
                        print("-" * 40)
                        print(resp.message)
                        print("-" * 40)

                    # prompt the user to edit the generated code code
                    edited = self.session.prompt(
                        "",
                        default=resp.code,
                    )
                    yield LLMCodeInput(
                        message=resp.message,
                        prompt=resp.prompt,
                        code=edited,
                        raw_resp=resp.raw,
                    )
                elif isinstance(resp, LLMResponseMessage):
                    yield LLMMessageInput(
                        prompt=resp.prompt, message=resp.message, raw_resp=resp.raw
                    )
                elif isinstance(resp, LLMError):
                    yield LLMErrorInput(
                        prompt=resp.prompt, error=resp.error, raw_resp=resp.raw
                    )
                continue

            # handle the history command
            if line.startswith("history"):
                nodes = self.console.history_tree.lineage()
                for node in nodes:
                    print(f"[{node.depth}]: {node.data}")
                continue

            # if we are here, assume the line is user code
            yield UserInput(line)

    def go(self):
        inputs = self.input_generator()
        for line in inputs:
            try:
                resp = self.console.handle_line(line)
                if resp is not None:
                    print(resp, end="")
            except KeyboardInterrupt:
                # Handle Ctrl+C and reset the lines
                self.multiline = False
            except EOFError:
                # Handle Ctrl+D (exit)
                print("\nGoodbye!")
                break
