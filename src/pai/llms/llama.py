from typing import Any, Generator
from pai.history import HistoryNode
from pai.llms.llm_protocol import (
    LLM,
    LLMError,
    LLMResponse,
    LLMResponseCode,
    LLMStreamChunk,
)
from llama_cpp import CompletionChunk, Iterator, Llama


class LlamaCpp(LLM):
    llama: Llama

    def __init__(self, model_location: str) -> None:
        self.llama = Llama(model_location, verbose=False)

    def description(self) -> str:
        return f"llama.cpp: {self.llama.model_path}"

    def prompt(self, history: list[HistoryNode], prompt: str) -> str:
        full_prompt = """print hello\n```python\nprint("hello")\n```\nout: hello\n"""

        # build the messages from the history
        for node in history:
            if isinstance(node.data, HistoryNode.Root):
                # skip the root node
                continue
            if isinstance(node.data, HistoryNode.UserCode):
                full_prompt += (
                    f"```python\n{node.data.code}\n```\nout: {node.data.result}\n"
                )
            elif isinstance(node.data, HistoryNode.LLMCode):
                full_prompt += f"{node.data.prompt}\n```python\n{node.data.code}\n```\nout: {node.data.result}\n"
            elif isinstance(node.data, HistoryNode.LLMMessage):
                full_prompt += f"{node.data.prompt}\n: {node.data.message}"
            elif isinstance(node.data, HistoryNode.LLMError):
                full_prompt += f"{node.data.prompt}\n: {node.data.error}"

        full_prompt += f"\n{prompt}\n```python\n"

        return full_prompt

    def call(
        self, history: list[HistoryNode], prompt: str
    ) -> Generator[LLMStreamChunk, None, LLMResponse]:
        full_prompt = self.prompt(history, prompt)

        resp = self.llama(prompt=full_prompt, max_tokens=64, stop=["```"], stream=True)

        full_text = ""
        for chunk in resp:
            text = chunk["choices"][0]["text"]  # type: ignore
            full_text += text
            yield LLMStreamChunk(text=text)

        # if full text doesn't end with a newline, yield one
        if not full_text.endswith("\n"):
            yield LLMStreamChunk(text="\n")

        return LLMResponseCode(
            prompt=prompt,
            code=full_text,
            message=None,
            raw=None,
        )
