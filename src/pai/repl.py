import sys
import threading
import time
from typing import Generator, Tuple

from prompt_toolkit import HTML, PromptSession, print_formatted_text
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys
from prompt_toolkit.styles import Style
from pai.util import get_version_from_pyproject


from pai.console import (
    Console,
    ConsoleInput,
    LLMCodeInput,
    LLMErrorInput,
    LLMMessageInput,
    UserInput,
)
from pai.llms.llm_protocol import LLMError, LLMResponseCode, LLMResponseMessage


def spinner_generator() -> Generator[str, None, None]:
    """Generate spinner frames."""
    while True:
        yield "| Generating response..."
        yield "/ Generating response..."
        yield "- Generating response..."
        yield "\\ Generating response..."


def spinner_animation(event: threading.Event):
    """Spinner animation function to be run in a separate thread."""
    spinner = spinner_generator()
    while not event.is_set():
        print(next(spinner), end="\r", flush=True)
        time.sleep(0.1)
    print(" " * 2, end="\r", flush=True)  # Clear the spinner


class Animation:
    """Context manager for spinner animation."""

    def __enter__(self):
        self.stop_event = threading.Event()
        self.spinner_thread = threading.Thread(
            target=spinner_animation, args=(self.stop_event,)
        )
        self.spinner_thread.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop_event.set()
        self.spinner_thread.join()


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
    console: Console
    session: PromptSession
    multiline: bool
    buffered_lines: list[str]

    def __init__(self, console: Console):
        self.console = console
        self.session = PromptSession(key_bindings=key_bindings)
        self.multiline = False
        self.buffered_lines = []
        self.agent = False

    def _current_index(self) -> int:
        """Get the current index of the history tree."""
        return self.console.history_tree.current_position().depth

    def _inp_prompt(self) -> HTML:
        """Generate the input prompt."""
        return HTML(f"<inp>Inp [{self._current_index()}]> </inp>")

    def _gen_prompt(self) -> HTML:
        """Generate the code gen prompt."""
        return HTML(f"<gen>Gen [{self._current_index()}]> </gen>")

    def _multi_prompt(self) -> HTML:
        """Generate the multi-line prompt."""
        ellipsis = "." * (2 + len(str(self._current_index())))
        return HTML(f"<multi>    {ellipsis}> </multi>")

    def _handle_console_input(self, console_inp: ConsoleInput):
        """Push a line input to the console and print the result."""
        resp = self.console.handle_line(console_inp)
        if resp:
            out = HTML(f"<out>Out [{self._current_index()}]></out> ")
            print_formatted_text(out, style=prompt_style, end="")
            print(resp, end="")

    def _handle_code_gen(self, prompt: str) -> ConsoleInput:
        """
        Handle the code gen command.
        - Takes a prompt and generates code using the LLM.
        - Prompts the user to edit (or cancel) the generated code.
        - The edited code is pushed to the console.
        """
        with Animation():
            resp = self.console.gen_code(prompt)

        if isinstance(resp, LLMResponseCode):
            # print the message of the response
            if resp.message:
                print(resp.message)

            # prompt the user to edit the generated code
            edited = self.session.prompt(
                self._gen_prompt(),
                default=resp.code,
                prompt_continuation=self._multi_prompt(),
                style=prompt_style,
            )

            # push the edited code to the console
            line_input = LLMCodeInput(
                prompt=resp.prompt,
                message=resp.message,
                code=edited,
                raw_resp=resp.raw,
            )
            return line_input
        elif isinstance(resp, LLMResponseMessage):
            # if the response is a message, then print the message
            line_input = LLMMessageInput(
                prompt=resp.prompt, message=resp.message, raw_resp=resp.raw
            )
            return line_input
        elif isinstance(resp, LLMError):
            # if the response is an error, then print the error
            line_input = LLMErrorInput(
                prompt=resp.prompt, error=resp.error, raw_resp=resp.raw
            )
            return line_input
        else:
            # Either the llm returned UserInput (not ok)
            # or it returned a type that we don't know about (also not ok)
            # Should not happen, but to be safe we'll raise an exception
            raise Exception(f"LLM returned an invalid response: {resp}")

    def go(self):
        print(f"pai {get_version_from_pyproject()} - {self.console.llm.description()}")
        print("Type 'pai: <prompt>' to generate code")
        print("'Ctrl+D' to exit. 'Ctrl+o' to insert a newline.")

        while True:
            try:
                # get the next str input from the user
                line: str = self.session.prompt(
                    self._inp_prompt(),
                    prompt_continuation=self._multi_prompt(),
                    style=prompt_style,
                )

                if line.startswith("gen:"):
                    # handle the one off code gen command
                    line = line[4:]  # remove the "pai:" prefix
                    console_input = self._handle_code_gen(line)
                    self._handle_console_input(console_input)
                elif line.startswith("pai:"):
                    # handle the "agent" command
                    if not self.console.llm.agent_support():
                        print("Agent support is not enabled for this LLM.")
                        continue

                    print("Agent mode started. Ctrl+C to exit.")

                    line = line[6:]  # remove the "agent:" prefix

                    # an agent is basically a gen code loop
                    # we'll keep generating code until the llm returns a non-code message or the user cancels
                    self.agent = True
                    while self.agent:
                        console_input = self._handle_code_gen(line)
                        if isinstance(console_input, LLMMessageInput):
                            # if the llm returned a message, then print the message and exit the agent
                            self._handle_console_input(console_input)
                            self.agent = False
                        elif isinstance(console_input, LLMErrorInput):
                            # if the llm returned an error, then print the error and exit the agent
                            self._handle_console_input(console_input)
                            self.agent = False
                        else:
                            # if the llm returned code, then push the code to the console
                            self._handle_console_input(console_input)

                elif line.startswith("history"):
                    # print the history
                    nodes = self.console.get_history()
                    for node in nodes:
                        print(f"[{node.depth}]: {node.data}")
                elif line.startswith("prompt:"):
                    # preview a prompt
                    line = line[7:]
                    llm_prompt = self.console.get_prompt(line)
                    print(llm_prompt)
                else:
                    # if we make it here, then the line is normal user input
                    line_input = UserInput(line)
                    self._handle_console_input(line_input)

            except KeyboardInterrupt as e:
                # Handle Ctrl+C and reset the lines
                self.multiline = False
                self.agent = False
                string_error = str(e)
                if string_error:
                    print(string_error)
                continue
            except EOFError:
                # Handle Ctrl+D (exit)
                print("\nGoodbye!")
                break
