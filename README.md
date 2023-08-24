# pai: A Python REPL with built in LLM support

Describe your task by typing `ai: <prompt>`, and pai generates the Python code for you using the REPL history as context

## Demo

```
Inp [0]> nums = [1,2,3,4,5,6,7,8]
Inp [1]> nums
Out [1]> [1, 2, 3, 4, 5, 6, 7, 8]
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
```