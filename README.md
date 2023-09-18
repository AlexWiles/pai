# pai: An AI agent inside your Python REPL

[![PyPI - Version](https://img.shields.io/pypi/v/pai-repl)](https://pypi.org/project/pai-repl/)


A Python REPL with a built in AI agent and code generation.

## Features
- Full Python REPL
- Built-in AI agent that can generate and run code in the REPL
- REPL history is used for LLM context.
- Edit and approve all generated code before it is executed
- Runs locally on your machine, so it has full system and internet access
- Supports OpenAI and llama.cpp

## Demo

<img src="./assets/graph.gif" />

## Installation
```
pip install pai-repl
```

## Usage

### OpenAI models
The default model is OpenAI GPT-4. You will need to set your OpenAI API key.
```
$ export OPENAI_API_KEY=<your key>
$ pai
```

Specify OpenAI model
```
$ pai --openai gpt-3.5-turbo
```

### llama.cpp compatible models

`llama-cpp-python` is an optional dependency because it requires native libraries to be installed so it must be installed using the `llama` extra.
```
$ pip install pai-repl[llama]
$ pai --llama <path to model>
```

### Starting the REPL

When you invoke `pai`, it will start an interactive Python REPL.

```
$ pai
INP [0]> print('howdy')
OUT [1]> howdy
```

### Start the agent

Start the agent with `pai: <prompt>`.

This will generate code using the prompt and REPL history. You can accept, edit or cancel the code. Immediately after the generated code is run, the LLM is called again with the new REPL history. This loop continues until the task is complete or you cancel the agent with `Ctrl+C`.


```
INP [0]> pai: list files in the current directory
LLM [0]>
import os
os.listdir()

OK? [0]> import os
    ...> os.listdir()
```


### One off code generation
Generate code with `gen: <prompt>`.

The generated code will be displayed and you can accept, edit or cancel it. Unlike the `pai` command, the LLM is not called again after the code is run.

```
INP [0]> nums = [1,2,3]
INP [1]> gen: average nums
LLM [1]>
# to find the average of the numbers, we sum all the elements and then divide by the number of elements

average_nums = sum(nums) / len(nums)
average_nums

OK? [1]> # to find the average of the numbers, we sum all the elements and then
    ...> divide by the number of elements
    ...>
    ...> average_nums = sum(nums) / len(nums)
    ...> average_nums
OUT [1]> 2.0
INP [2]>
```

### REPL features
`reset()` will reset the REPL state and history. This is useful if you want to start a new task or want to start over. No previous history will be used for LLM context.
```
INP [0]> a = 1
INP [1]> reset()
INP [0]> a
OUT [0]> Traceback (most recent call last):
  File "<console>", line 1, in <module>
NameError: name 'a' is not defined
INP [1]>
```

### Quickstart from the command line
You can prompt pai from the command line
```
$ pai "find the largest file in the current directory"
```
