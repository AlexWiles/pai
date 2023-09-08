# pai: It's like having code interpreter in your Python REPL
A Python REPL with a built in AI agents and code generation. REPL history is used for LLM context. Supports OpenAI and llama.cpp

You and the AI have access to the same REPL history, so you can guide the AI and move seamlessly between the two.

<img src="./assets/graph.gif" />

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

Prompt pai from the command line
```
$ pai "find the largest file in the current directory"
```

## AI Agent
Prompt the AI agent to complete a task by typing `pai: <prompt>`. The AI agent will continuously generate and run code until it completes the task or fails. All generated code must be approved by the user.

The task: "pai: there is a csv in the current directory. find it and give me a full analysis"

<img src="./assets/agent.gif" />

## Generate code

Generate code in the REPL by type `gen: <prompt>`. The generated code will be displayed and you can accept, edit or cancel it.

<img src="./assets/gen.gif" />