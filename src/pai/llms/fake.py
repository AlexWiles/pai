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

    def call(self, history: list[HistoryNode], prompt: str) -> LLMResponse:
        if prompt == "indent":
            code = "for i in range(2):\n    for j in range(2):\n        print(i, j)\n\n    for k in range(2):\n        print(i, k)\n"
            return LLMResponseCode(
                prompt=prompt,
                code=code,
                message=None,
                raw=None,
            )

        return LLMResponseCode(
            prompt=prompt,
            code="import os\nos.listdir()",
            message="This code will list the files",
            raw=None,
        )
