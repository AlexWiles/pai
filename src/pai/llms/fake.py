import time
from typing import Any, Generator
from pai.history import HistoryNode
from pai.llms.llm_protocol import (
    LLM,
    LLMError,
    LLMResponse,
    LLMResponseCode,
    LLMResponseMessage,
    LLMStreamChunk,
)


def chunk_string(s, n):
    """Divide the string s into chunks of size n."""
    return [s[i : i + n] for i in range(0, len(s), n)]


class FakeLLM(LLM):
    def prompt(self, history: list[HistoryNode], prompt: str) -> Any:
        return prompt

    def description(self) -> str:
        return "FakeLLM"

    def call(
        self, history: list[HistoryNode], prompt: str
    ) -> Generator[LLMStreamChunk, None, LLMResponse]:
        message = "This code will list the files\nin the current directory. \n```python\nimport os\nos.listdir()\n```\n"

        # chuck the message by 7 characters
        for s in chunk_string(message, 7):
            yield LLMStreamChunk(s)
            time.sleep(0.2)

        return LLMResponseCode(
            prompt=prompt,
            code="import os\nos.listdir()",
            message="This code will list the files\nin the current directory.",
            raw=None,
        )
