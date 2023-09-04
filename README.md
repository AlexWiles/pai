# pai: a Python REPL with built in code generation and AI agents
A Python REPL with a built in AI agents and code generation. REPL history is used for LLM context. Supports OpenAI and llama.cpp

## Installation
```
pip install pai-repl
```

## Command line usage
When you invoke `pai`, it will start an interactive Python REPL with a built in AI agent.

```
$ pai
INP [0]>
```


Use with OpenAI. The default model is `gpt-4`
```
$ export OPENAI_API_KEY=<your key>
$ pai
```

Specify OpenAI model
```
$ pai --openai gpt-3.5-turbo
```

Use with llama.cpp compatible models
```
$ pai --llama <path to model>
```

Specify an initial prompt for the AI agent
```
$ pai "find the largest file in the current directory"
```

## Generate code

Generate code in the REPL by type `gen: <prompt>`. The generated code will be displayed and you can accept, edit or cancel it.

<img src="./assets/gen.gif" />


## Start the AI Agent
Prompt the AI agent to complete a task by typing `pai: <prompt>`. The AI agent will continuously generate and run code until it completes the task or fails. All generated code must be approved by the user.

The task: "pai: there is a csv in the current directory. find it and give me a full analysis"

<img src="./assets/agent.gif" />