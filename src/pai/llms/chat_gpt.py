import json
from typing import Any, Generator, List, Optional
import openai

from pai.history import HistoryNode
from pai.llms.llm_protocol import (
    LLM,
    LLMError,
    LLMResponse,
    LLMResponseCode,
    LLMResponseMessage,
    LLMStreamChunk,
)

DEFAULT_SYS_PROMPT = f"""
Your name is "pai", you're an expert Python engineer.
Execute Python in a REPL to tackle problems.
Use subprocess for shell commands.
All code is security-approved by an expert.
Users see REPL history.
Only indicate task completion; if not, assess recent output and proceed.
Approach problems systematically, gather data, segment tasks, and solve with Python.
Full system and internet access granted.
"""


class ChatGPT(LLM):
    model: str
    sys_prompt: str

    def __init__(self, model: str, sys_prompt: str = DEFAULT_SYS_PROMPT) -> None:
        self.model = model
        self.sys_prompt = sys_prompt

    def agent_support(self) -> bool:
        return True

    def description(self) -> str:
        return f"{self.model}"

    def prompt(
        self,
        history: List[HistoryNode],
        prompt: str,
    ) -> Any:
        messages = [
            {
                "role": "system",
                "content": self.sys_prompt,
            },
        ]

        # build the messages from the history
        for node in history:
            if isinstance(node.data, HistoryNode.Root):
                # skip the root node
                continue
            if isinstance(node.data, HistoryNode.UserCode):
                # check if the last message is user code.
                # if it is, then add the node data to the last message. if it isn't, then add a new message
                if messages[-1]["role"] == "user":
                    messages[-1][
                        "content"
                    ] += f">>>{node.data.code}\\n{node.data.result}\\n"
                else:
                    messages.append(
                        {
                            "role": "user",
                            "content": f">>>{node.data.code}\\n{node.data.result}\\n",
                        }
                    )
            elif isinstance(node.data, HistoryNode.LLMCode):
                messages.extend(
                    [
                        {"role": "user", "content": f"{node.data.prompt}"},
                        {
                            "role": "assistant",
                            "content": None,  # type: ignore
                            "function_call": {
                                "name": "python",
                                "arguments": json.dumps({"code": node.data.code}),
                            },
                        },
                        {
                            "role": "function",
                            "name": "python",
                            "content": f"{node.data.result}",
                        },
                    ]
                )
            elif isinstance(node.data, HistoryNode.LLMMessage):
                messages.extend(
                    [
                        {"role": "user", "content": f"{node.data.prompt}"},
                        {"role": "assistant", "content": f"{node.data.message}"},
                    ]
                )
            elif isinstance(node.data, HistoryNode.LLMError):
                messages.extend(
                    [
                        {"role": "user", "content": f"{node.data.prompt}"},
                        node.data.raw_resp.choices[0].message,
                        {"role": "user", "content": f"{node.data.error}"},
                    ]
                )

        # if there is a user prompt, then add it to the messages
        if prompt.strip() != "":
            if messages[-1]["role"] == "user":
                # if the last message is a user prompt, then add the prompt to the last message
                messages[-1]["content"] += f"\\n{prompt}"
            else:
                # if the last message is not a user prompt, then add a new message
                messages.append({"role": "user", "content": f"{prompt}"})

        return messages

    def call(
        self, history: List[HistoryNode], prompt: str
    ) -> Generator[LLMStreamChunk, None, LLMResponse]:
        messages = self.prompt(history, prompt)

        resp: Any = openai.ChatCompletion.create(
            model=self.model,
            messages=messages,
            # function_call={"name": "python"},
            functions=[
                {
                    "name": "python",
                    "description": "Execute Python code in the REPL.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "code": {
                                "type": "string",
                                "description": "The Python code to run",
                            },
                        },
                    },
                }
            ],
            stream=True,
        )

        raw_chunks = []
        response_text = ""
        func_call = {
            "name": "",
            "arguments": "",
        }

        # this is nasty
        for response_chunk in resp:
            if "choices" in response_chunk:
                deltas = response_chunk["choices"][0]["delta"]
                if "function_call" in deltas:
                    if "name" in deltas["function_call"]:
                        func_call["name"] = deltas["function_call"]["name"]
                    if "arguments" in deltas["function_call"]:
                        func_call["arguments"] += deltas["function_call"]["arguments"]
                        yield LLMStreamChunk(deltas["function_call"]["arguments"])
                elif "content" in deltas:
                    response_text += deltas["content"]
                    yield LLMStreamChunk(deltas["content"])
                if response_chunk["choices"][0]["finish_reason"] == "function_call":
                    yield LLMStreamChunk(f"\n")
            raw_chunks.append(response_chunk)

        yield LLMStreamChunk(f"\n")

        # check if the response is a function call
        if func_call["name"] != "":
            # parse the arguments as json
            # expecting something like {"code": "print('hello world')"}
            try:
                j = json.loads(func_call["arguments"])
            except json.JSONDecodeError as e:
                # sometimes the function call arguments are just code, not a json object
                # rather than erroring, we check if it is valid python code and return it if it is
                try:
                    compile(func_call["arguments"], "<string>", "exec")
                    # if it is valid python code, then we return a LLMResponseCode
                    return LLMResponseCode(
                        prompt=prompt,
                        code=func_call["arguments"],
                        message=response_text or None,
                        raw=raw_chunks,
                    )
                except SyntaxError:
                    # return the original JSONDecodeError
                    return LLMError(prompt=prompt, error=str(e), raw=resp)

            return LLMResponseCode(
                prompt=prompt,
                code=j["code"],
                message=response_text or None,
                raw=raw_chunks,
            )
        else:
            return LLMResponseMessage(
                prompt=prompt,
                message=response_text,
                raw=raw_chunks,
            )
