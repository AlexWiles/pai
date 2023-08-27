# pai
A Python REPL with a built in AI agent that uses prior REPL history for context.

Supports OpenAI and llama.cpp

## Installation
```
pip install pai-repl
```

## Features

### Code Generation
Generate code by typing `gen: <prompt>`. You can accept, edit or cancel the generated code.

**Example**

Generate code that operates on a variable setup by the user.
```
Inp [0]> nums = [1,2,3,3,3,3,3,3,3,4]
Inp [1]> gen: what is the mean of nums?
Gen [1]> import statistics
    ...>
    ...> mean = statistics.mean(nums)
    ...> mean
Out [2]> 2.8
```

### AI Agent
Ask an AI agent to complete a task. It will continuously generate and run code until it completes the task or fails. All generated code must be approved by the user.



## Usage with OpenAI
```
pai --gpt-4
```

## Examples

### Access to REPL history as context
```
Inp [0]> nums = [1,2,3,4,5,6,7,8]
Inp [2]> ai: calc mean, median and mode. assign each to a var
Gen [2]> from statistics import mean, median, mode
    ...>
    ...> mean_val = mean(nums)
    ...> median_val = median(nums)
    ...> try:
    ...>     mode_val = mode(nums)
    ...> except:
    ...>     mode_val = 'No mode'
    ...>
    ...> mean_val, median_val, mode_val
Out [2]> (4.5, 4.5, 1)
Inp [3]> mean_val
Out [3]> 4.5
```

### Local filesystem access
```
Inp [0]> ai: list markdown files in the current directory
Gen [0]> import os
    ...>
    ...> # List all markdown files in the current directory
    ...> markdown_files = [file for file in os.listdir() if file.endswith('.md')]
    ...>
    ...> markdown_files
Out [0]> ['README.md']
```
# CLI Flags
The CLI accepts the following flags:

- `--llama-cpp`: Use LlamaCpp as the LLM with the given model location.
- `--openai`: Use ChatGPT as the LLM with the given model. Requires OPENAI_API_KEY in the environment.
- `--ctx-history-count`: Determines how many history nodes to send to the LLM as context. Defaults to all of them.
- `--version`: Displays the version.
