from abc import abstractmethod
from typing import Any, Generator, List, Optional, Protocol, Union
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


@dataclass
class LLMStreamChunk:
    text: str


LLMResponse = Union[LLMResponseCode, LLMResponseMessage, LLMError]


class LLM(Protocol):
    def agent_support(self) -> bool:
        return False

    @abstractmethod
    def call(
        self, history: List[HistoryNode], prompt: str
    ) -> Generator[LLMStreamChunk, None, LLMResponse]:
        ...

    @abstractmethod
    def prompt(self, history: List[HistoryNode], prompt: str) -> Any:
        ...

    @abstractmethod
    def description(self) -> str:
        """Return a description of the LLM."""
        ...
