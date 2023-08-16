import json
from typing import Any
import openai

from pai.history import HistoryNode
from pai.llms.llm import LLM, LLMError, LLMResponse, LLMResponseCode, LLMResponseMessage


class ChatGPT(LLM):
    model: str = "gpt-4"

    def __init__(self, model: str) -> None:
        self.model = model

    def call(self, history: list[HistoryNode], prompt: str) -> LLMResponse:
        # build the system prompt using the command history
        messages = [
            {
                "role": "system",
                "content": "You are a Python programmer executing code in a REPL with full internet and file system access.",
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

        # add the user prompt. if the last message is a user prompt, then add the prompt to the last message
        if messages[-1]["role"] == "user":
            messages[-1]["content"] += f"\\n{prompt}"
        else:
            messages.append({"role": "user", "content": f"{prompt}"})

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
        )

        new_msg = resp.choices[0].message

        # check if the response is a function call
        if new_msg.get("function_call", None):
            # parse the arguments as json
            # expecting something like {"code": "print('hello world')"}
            try:
                j = json.loads(new_msg.function_call.arguments)
            except json.JSONDecodeError as e:
                # sometimes the function call arguments are just code, not a json object
                # rather than erroring, we check if it is valid python code and return it if it is
                try:
                    compile(new_msg.function_call.arguments, "<string>", "exec")
                    # if it is valid python code, then we return a LLMResponseCode
                    return LLMResponseCode(
                        prompt=prompt,
                        code=new_msg.function_call.arguments,
                        message=new_msg.get("content", None),
                        raw=resp,
                    )
                except SyntaxError:
                    # return the original JSONDecodeError
                    return LLMError(prompt=prompt, error=str(e), raw=resp)

            return LLMResponseCode(
                prompt=prompt,
                code=j["code"],
                message=new_msg.get("content", None),
                raw=resp,
            )
        else:
            return LLMResponseMessage(
                prompt=prompt,
                message=new_msg.content,
                raw=resp,
            )
