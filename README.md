# pai: A Python REPL with built in LLM support

- Promp the LLM by inputting `ai: <prompt>`. Pai will use the REPL history as context and generate code.
- Review, modify, and confirm all generated code prior to execution.
- Operates natively on your system, providing unrestricted access to both disk and network resources.

## Installation & Usage
```
pip install pai-repl
$ export OPENAI_API_KEY=<api key>
$ pai
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