from typing import Any
from pai.history import HistoryNode
from pai.llms.llm_protocol import (
    LLM,
    LLMError,
    LLMResponse,
    LLMResponseCode,
    LLMResponseMessage,
)


class FakeLLM(LLM):
    def prompt(self, history: list[HistoryNode], prompt: str) -> Any:
        return prompt

    def description(self) -> str:
        return "FakeLLM"

    def call(self, history: list[HistoryNode], prompt: str) -> LLMResponse:
        return LLMResponseCode(
            prompt=prompt,
            code="import os\nos.listdir()",
            message="This code will list the files",
            raw=None,
        )
