import json
from typing import Any, Generator
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


system_prompt = """
You are a helpful AI assistant

You can execute Python code in a REPL context.
You can access and modify previously defined variables and functions.
You can access the internet
You can access the file system

Do not redefine variables or functions that are already defined.
Do not repeat the output of the code, the user can already see it.
Do not repeat the same code over and over.
Do not assume things like what operating system you are running on. Use python to find out.

All code you write will be approved by a human before it is executed.

When you execute Python code, the output will be given to you.
If the task is complete, summarize the findings.
If a task is not complete, analyze the latest output and continue.

Think through a problem step by step.
Break a problem into sub problems.
Use code to solve sub problems.
"""


class ChatGPT(LLM):
    model: str = "gpt-4"

    def __init__(self, model: str) -> None:
        self.model = model

    def agent_support(self) -> bool:
        return True

    def description(self) -> str:
        return f"ChatGPT: {self.model}"

    def prompt(self, history: list[HistoryNode], prompt: str) -> Any:
        # build the system prompt using the command history
        messages = [
            {
                "role": "system",
                "content": system_prompt,
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
        self, history: list[HistoryNode], prompt: str
    ) -> Generator[LLMStreamChunk, None, LLMResponse]:
        # make it an empty generator
        yield from []

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

        for response_chunk in resp:
            # print(response_chunk)
            if "choices" in response_chunk:
                deltas = response_chunk["choices"][0]["delta"]
                if "function_call" in deltas:
                    if "name" in deltas["function_call"]:
                        func_call["name"] = deltas["function_call"]["name"]
                        yield LLMStreamChunk(f"\n```python\n")
                    if "arguments" in deltas["function_call"]:
                        func_call["arguments"] += deltas["function_call"]["arguments"]
                        yield LLMStreamChunk(deltas["function_call"]["arguments"])
                elif "content" in deltas:
                    # if the last message is a function call, close the md code block
                    if (
                        len(raw_chunks) > 0
                        and "function_call" in raw_chunks[-1]["choices"][0]["delta"]
                    ):
                        yield LLMStreamChunk(f"\n```\n")
                    response_text += deltas["content"]
                    yield LLMStreamChunk(deltas["content"])
                if response_chunk["choices"][0]["finish_reason"] == "function_call":
                    yield LLMStreamChunk(f"\n```")
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
