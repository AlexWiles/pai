# pai
A Python REPL that employs language models to generate code, using prior REPL history for context. Supports OpenAI and llama.cpp

## Features
- Generate code in the REPL by typing `pai: <prompt>`
- REPL history used as context for the LLM prompt
- Review, edit and confirm all generated code prior to execution.
- Code executes on your machine.
- Supports ChatGPT and llama.cpp

## Installation & Usage
```
pip install pai-repl
$ export OPENAI_API_KEY=<api key>
$ pai --chat-gpt gpt-4
Inp [0]>
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