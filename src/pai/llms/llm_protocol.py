from abc import abstractmethod
from typing import Any, Optional, Protocol
from pydantic.dataclasses import dataclass

from pai.history import HistoryNode


@dataclass
class LLMResponseCode:
    prompt: str
    message: Optional[str]
    code: str
    raw: Any


@dataclass
class LLMResponseMessage:
    prompt: str
    message: str
    raw: Any


@dataclass
class LLMError:
    prompt: str
    error: str
    raw: Any


LLMResponse = LLMResponseCode | LLMResponseMessage | LLMError


class LLM(Protocol):
    @abstractmethod
    def call(self, history: list[HistoryNode], prompt: str) -> LLMResponse:
        ...

    def prompt(self, history: list[HistoryNode], prompt: str) -> Any:
        ...
