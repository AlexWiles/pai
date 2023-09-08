# pai: An AI agent inside your Python REPL

A Python REPL with a built in AI agent and code generation.

- REPL history is used for LLM context.
- All code can be edited or cancelled before execution
- Runs locally on your machine, so it has full system and internet access
- Supports OpenAI and llama.cpp


<img src="./assets/graph.gif" />

## Installation
```
pip install pai-repl
```

## Usage
When you invoke `pai`, it will start an interactive Python REPL.

```
$ pai
INP [0]> nums = [1,2,3]
INP [1]> nums[0]
OUT [1]> 1
INP [2]>
```

Generate code with `gen: <prompt>`. The generated code will be displayed and you can accept, edit or cancel it.

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

Start the agent with `pai: <prompt>`. The agent will continuously generate and run code until it completes the task or fails.

```
INP [0]> pai: pick 2 random wikipedia articles and tell me how they are related
LLM [0]>
# Let's use the wikipedia API to fetch random articles
import requests
import json

def get_random_wikipedia_articles(count):
    S = requests.Session()
    ...
```

Prompt pai from the command line
```
$ pai "find the largest file in the current directory"
```

## Configuration

The default model is OpenAI GPT-4. You will need to set your OpenAI API key.
```
$ export OPENAI_API_KEY=<your key>
$ pai
pai v0.1.12 using gpt-4
'Ctrl+D' to exit. 'Ctrl+o' to insert a newline.
INP [0]>
```

Specify OpenAI model
```
$ pai --openai gpt-3.5-turbo
```

Alternatively, you can use llama.cpp compatible models
```
$ pai --llama <path to model>
```

