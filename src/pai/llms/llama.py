from typing import Any
from pai.history import HistoryNode
from pai.llms.llm_protocol import LLM, LLMError, LLMResponse, LLMResponseCode
from llama_cpp import Iterator, Llama


class LlamaCpp(LLM):
    llama: Llama

    def __init__(self, model_location: str) -> None:
        self.llama = Llama(model_location, verbose=False)

    def prompt(self, history: list[HistoryNode], prompt: str) -> Any:
        full_prompt = ""

        # build the messages from the history
        for node in history:
            if isinstance(node.data, HistoryNode.Root):
                # skip the root node
                continue
            if isinstance(node.data, HistoryNode.UserCode):
                full_prompt += f"{node.data.code}\n# out: {node.data.result}\n"
            elif isinstance(node.data, HistoryNode.LLMCode):
                full_prompt += f"# {node.data.prompt}\n{node.data.code}\n# out: {node.data.result}\n"
            elif isinstance(node.data, HistoryNode.LLMMessage):
                full_prompt += f"# {node.data.prompt}\n# {node.data.message}"
            elif isinstance(node.data, HistoryNode.LLMError):
                full_prompt += f"# {node.data.prompt}\n# {node.data.error}"

        full_prompt += f"\n# {prompt}\n"

        return full_prompt

    def call(self, history: list[HistoryNode], prompt: str) -> LLMResponse:
        full_prompt = self.prompt(history, prompt)

        resp = self.llama(
            prompt=full_prompt, max_tokens=64, stop=["\n\n"], stream=False
        )

        if isinstance(resp, Iterator):
            # Should not happen, but to be safe we'll raise an exception
            raise Exception("LlamaCpp returned an iterator")
        else:
            return LLMResponseCode(
                prompt=prompt,
                code=resp["choices"][0]["text"],
                message=None,
                raw=None,
            )
