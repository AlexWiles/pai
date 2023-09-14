import sys
import threading
import time
from typing import Generator, Optional, Tuple

from prompt_toolkit import HTML, PromptSession, print_formatted_text
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys
from prompt_toolkit.styles import Style
from pai.version import VERSION


from pai.console import (
    PaiConsole,
    ConsoleInput,
    LLMCodeInput,
    NewLLMMessage,
    CodeResult,
    UserInput,
    WaitingForInputApproval,
    WaitingForInput,
    WaitingForLLM,
)
from pai.llms.llm_protocol import LLMStreamChunk


# Create a session object
key_bindings = KeyBindings()


@key_bindings.add(Keys.Tab)
def _(event):
    "Insert four spaces for tab key."
    event.cli.current_buffer.insert_text("    ")


@key_bindings.add("escape", "enter")
@key_bindings.add("c-o")
def _(event):
    "Bind meta+enter or esc+enter to insert a newline."
    event.current_buffer.insert_text("\n")


@key_bindings.add("enter")
def _(event):
    event.current_buffer.validate_and_handle()


prompt_style = Style.from_dict(
    {
        "inp": "bold",
        "gen": "bold",
        "multi": "bold",
        "out": "bold",
    }
)


class REPL:
    console: PaiConsole
    session: PromptSession
    current_history_index: int

    def __init__(self, console: PaiConsole):
        self.console = console
        self.session = PromptSession(key_bindings=key_bindings)
        self.current_history_index = -1

    def _current_index(self) -> int:
        """Get the current index of the history tree."""
        return self.console.history_tree.current_position().depth

    def _inp_prompt(self) -> HTML:
        """Generate the input prompt."""
        return HTML(f"<inp>INP [{self._current_index()}]> </inp>")

    def _gen_prompt(self) -> HTML:
        """Generate the code gen prompt."""
        return HTML(f"<gen>LLM [{self._current_index()}]> </gen>")

    def _ok_prompt(self) -> HTML:
        """Generate the code gen prompt."""
        return HTML(f"<gen>OK? [{self._current_index()}]> </gen>")

    def _out_prompt(self) -> HTML:
        """Generate the output prompt."""
        return HTML(f"<out>OUT [{self._current_index()}]> </out>")

    def _multi_prompt(self) -> HTML:
        """Generate the multi-line prompt."""
        ellipsis = "." * (2 + len(str(self._current_index())))
        return HTML(f"<multi>    {ellipsis}> </multi>")

    def _handle_console_input(self, console_inp: ConsoleInput):
        """Push a line input to the console and print the result."""
        resp = self.console.handle_input(console_inp)
        if resp:
            print_formatted_text(self._out_prompt(), style=prompt_style, end="")
            print(resp, end="")

    def go(self, initial_prompt: Optional[str] = None):
        print(f"pai v{VERSION} using {self.console.llm.description()}")
        print("'Ctrl+D' to exit. 'Ctrl+o' to insert a newline.")

        generator = self.console.initial_state_generator()

        if initial_prompt:
            print_formatted_text(self._inp_prompt(), style=prompt_style, end="")
            print(initial_prompt)
            generator = self.console.code_gen(initial_prompt, agent_mode=True)

        event = None
        last_event = None
        while True:
            try:
                last_event = event
                event = next(generator)  # Start the generator

                sys.stdout.flush()
                if isinstance(event, WaitingForInput):
                    # get the next str input from the user
                    line: str = self.session.prompt(
                        self._inp_prompt(),
                        prompt_continuation=self._multi_prompt(),
                        style=prompt_style,
                    )

                    if line.startswith("pai:"):
                        line = line[4:].strip()
                        generator = self.console.code_gen(line, agent_mode=True)
                    elif line.startswith("gen:"):
                        line = line[4:].strip()
                        generator = self.console.code_gen(line, agent_mode=False)
                    else:
                        generator = self.console.handle_input(UserInput(line))
                elif isinstance(event, WaitingForInputApproval):
                    # The LLM generated code but it hasn't been approved yet
                    # Now we prompt the user with the generated code
                    # So they can edit it, approve it, or cancel it
                    llm_code = event.code
                    edited: str = self.session.prompt(
                        self._ok_prompt(),
                        default=llm_code.code,
                        prompt_continuation=self._multi_prompt(),
                        style=prompt_style,
                    )

                    # push the edited code to the console
                    console_inp = LLMCodeInput(
                        prompt=llm_code.prompt,
                        message=llm_code.message,
                        code=edited,
                        raw_resp=llm_code.raw_resp,
                        agent_mode=llm_code.agent_mode,
                    )
                    generator = self.console.handle_input(console_inp)
                elif isinstance(event, CodeResult):
                    # print the general output
                    if event.value:
                        print_formatted_text(
                            self._out_prompt(), style=prompt_style, end=""
                        )
                        print(event.value, end="")
                        # print a newline if the output doesn't end with one
                        if not event.value.endswith("\n"):
                            print()
                elif isinstance(event, NewLLMMessage):
                    # only print the message if it wasn't just streamed
                    # we can tell by looking at the last event
                    if not isinstance(last_event, LLMStreamChunk):
                        # print the LLM output
                        print_formatted_text(
                            self._gen_prompt(), style=prompt_style, end=""
                        )
                        print(event.value, end="")
                        # print a newline if the output doesn't end with one
                        if not event.value.endswith("\n"):
                            print()
                elif isinstance(event, LLMStreamChunk):
                    if not isinstance(last_event, LLMStreamChunk):
                        print_formatted_text(self._gen_prompt(), style=prompt_style)
                    print(event.text, end="")
                elif isinstance(event, WaitingForLLM):
                    pass
                else:
                    raise ValueError(f"Unknown input state: {type(event)}")

            except KeyboardInterrupt as e:
                # Handle Ctrl+C (cancel)
                string_error = str(e)
                if string_error:
                    print(string_error)
                generator = self.console.initial_state_generator()
                continue
            except EOFError:
                # Handle Ctrl+D (exit)
                print("\nGoodbye!")
                break
