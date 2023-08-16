# pai: A Python REPL with built in LLM support

Describe your task, and pai generates the Python code for you using the REPL history as context

## Demo

```
>>> nums = [1,1,2,3,3,4,5]
>>> ai: calc mean median and mode of nums. assign each to a variable
import statistics

nums = [1,1,2,3,3,4,5]

mean = statistics.mean(nums)
median = statistics.median(nums)
mode = statistics.mode(nums)

mean, median, mode
(2.7142857142857144, 3, 1)
>>> mean
2.7142857142857144
>>> median
3
```