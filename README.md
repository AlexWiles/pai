# pai: a python REPL with an integrated LLM agent
A Python REPL with a built in AI agent that uses prior REPL history for context.

Supports OpenAI and llama.cpp

## Installation
```
pip install pai-repl
```

## Usage

Use with openai
```
$ export OPENAI_API_KEY=<your key>
$ pai --openai gpt-4
```

Use with llama.cpp compatible models

```
$ pai --llama <path to model>
```


## Features

### Code Generation
Generate code by typing `gen: <prompt>`. You can accept, edit or cancel the generated code.

**Example**

Generate code that operates on a variable setup by the user.
```
INP [0]> nums = [1,2,3,3,3,3,3,3,3,4]
INP [1]> gen: what is the mean of nums?
OK? [1]> import statistics
    ...>
    ...> mean = statistics.mean(nums)
    ...> mean
OUT [2]> 2.8
```

### AI Agent
Ask an AI agent to complete a task. It will continuously generate and run code until it completes the task or fails. All generated code must be approved by the user.

The task: "pai: there is a csv in the current directory. find it and give me a full analysis"

We can see the agent doing the following:
- Look for csvs
- Load the csv when it finds one
- Attempt to import pandas for analysis. This fails
- Self correct and use standard Python functionality to analyze the data
- Do some analysis and print the results

```
INP [0]> pai: there is a csv in the current directory. find it and give me a full analysis

First, let's list all the CSV files in the current directory.
OK? [0]> import os
    ...>
    ...> # List all files in the current directory
    ...> files = os.listdir()
    ...>
    ...> # Filter out the ones which are csv files
    ...> csv_files = [file for file in files if file.endswith('.csv')]
    ...>
    ...> csv_files
OUT [1]> ['running_data.csv']
The CSV file in the current directory is named 'running_data.csv'. Now, I will load the data and analyze it. Let's start by loading the data and looking at the first few rows to understand its structure.
OK? [1]> import pandas as pd
    ...>
    ...> # Load the csv file into a pandas DataFrame
    ...> data = pd.read_csv('running_data.csv')
    ...>
    ...> # Display the first few rows of the DataFrame
    ...> data.head()
OUT [2]> Traceback (most recent call last):
  File "<string>", line 1, in <module>
ModuleNotFoundError: No module named 'pandas'
It appears that the pandas library, which is typically used for data analysis in Python, is not available in this environment. However, I can still provide a basic analysis using standard Python functionality.

Let's first take a look at the contents of the CSV file.
OK? [2]> import csv
    ...>
    ...> # Open the csv file
    ...> with open('running_data.csv', 'r') as file:
    ...>     reader = csv.reader(file)
    ...>
    ...>     # Get the headers and the first few rows to get a sense of the data
    ...>     headers = next(reader)
    ...>     first_few_rows = [next(reader) for _ in range(5)]
    ...>
    ...> headers, first_few_rows
OUT [3]> (['Date', 'Distance', 'Speed', 'Duration'], [['2023-07-29', '10', '9', '1.1111111111111112'], ['2023-07-30', '10', '8', '1.25'], ['2023-07-31', '8', '10', '0.8'], ['2023-08-01', '3', '10', '0.3'], ['2023-08-02', '6', '9', '0.6666666666666666']])
OK? [3]>
    ...> # Iterate over the rows and analyze the data
    ...>
    ...> # Initialize some variables
    ...> num_rows = 0
    ...> sum_distance = 0
    ...> sum_speed = 0
    ...> sum_duration = 0
    ...>
    ...> with open('running_data.csv', 'r') as file:
    ...>     reader = csv.reader(file)
    ...>
    ...>     # Skip the header
    ...>     next(reader)
    ...>
    ...>     for row in reader:
    ...>         num_rows += 1
    ...>         sum_distance += float(row[1])
    ...>         sum_speed += float(row[2])
    ...>         sum_duration += float(row[3])
    ...>
    ...> # Compute the averages
    ...> average_distance = sum_distance / num_rows
    ...> average_speed = sum_speed / num_rows
    ...> average_duration = sum_duration / num_rows
    ...>
    ...> average_distance, average_speed, average_duration
OK? [4]> (5.666666666666667, 9.466666666666667, 0.6017760942760944)
OK? [5]> Here is the analysis of the data in the `running_data.csv` file:

The data contains four columns: Date, Distance, Speed, and Duration.

Here are a few rows from the data:

1. ['2023-07-29', '10', '9', '1.1111111111111112']
2. ['2023-07-30', '10', '8', '1.25']
3. ['2023-07-31', '8', '10', '0.8']
4. ['2023-08-01', '3', '10', '0.3']
5. ['2023-08-02', '6', '9', '0.6666666666666666']

In terms of overall metrics:

- The average distance is approximately 5.67 units.
- The average speed is approximately 9.47 units.
- The average duration is approximately 0.60 units.

Please note that these averages are calculated from the existing data in the CSV file.

These measures can give you a good understanding of the data you are dealing with and can be a good starting point for further analysis. Task complete.
INP [5]>
```
