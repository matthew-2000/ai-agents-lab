# 01 - Tool-Using Assistant

## Objective

Build a minimal agent loop that can decide when to call simple tools and when to answer directly.
This project is the clean starting point for the whole repository: narrow scope, low abstraction, fast iteration, and an explicit LLM-powered agent core paired with simple deterministic tools.

## Main Concept

This project teaches the core mechanic behind many practical agents: a loop that can inspect a request, decide whether a tool is needed, execute that tool, observe the result, and continue until it can produce a final answer.

The emphasis is on simplicity and clarity rather than sophistication. Before adding memory, planning, or multi-agent coordination, this project establishes a strong baseline for tool-aware reasoning.

## Realistic Use Case

A lightweight assistant that answers practical user questions by combining reasoning with simple tools such as search, calculator, weather, or mock APIs.

Examples:

- answer a factual question that requires a quick search
- solve a numerical task with a calculator instead of freehand reasoning
- check weather through a tool instead of inventing it
- combine small tool outputs into a useful final response

## Expected Architecture

A reasonable first version should remain deliberately small:

- single agent loop
- one LLM-driven decision layer for the observe, reason, act cycle
- tool selection and execution layer
- observation to reasoning to action cycle
- final response assembly
- lightweight logging or traces for debugging

## Possible Tools

Early versions can stay simple and mostly local or mocked:

- search
- calculator
- weather
- mock HTTP APIs

The goal is not breadth of tooling. The goal is to make tool choice, tool execution, and result integration explicit and inspectable.

## Scope Boundaries

This project should stay intentionally constrained.

- It is not a full assistant platform.
- It is not a production orchestration framework.
- It does not need memory, retrieval, or multi-agent behavior in v1.
- It should avoid unnecessary abstractions that belong to later projects.

## Directory Structure

```text
01-tool-using-assistant/
├── README.md
├── requirements.txt
├── .env.example
├── src/
│   └── main.py
├── evals/
│   ├── README.md
│   └── test_cases.json
├── data/
│   └── .gitkeep
├── logs/
│   └── .gitkeep
└── notes.md
```

## Current Project Status

Implemented as a narrow v1 agent using the OpenAI Responses API plus three deterministic local tools: calculator, mocked weather lookup, and local knowledge-base search.

The current folder is ready for iterative development, with room for local experiments, simple evals, and design notes without introducing cross-project dependencies.

## Running The Project

1. Install dependencies: `pip install -r requirements.txt`
2. Copy `.env.example` to `.env` and set `OPENAI_API_KEY`
3. Run a local tool sanity check: `python src/main.py --self-check`
4. Run one prompt end to end: `python src/main.py --prompt "What is 17 * 24?"`
5. Or start the interactive loop: `python src/main.py`

## Suggested Next Steps

1. Define a minimal tool interface.
2. Replace one mocked tool with a live external integration.
3. Add a simple eval harness for `evals/test_cases.json`.
4. Compare direct answering versus tool-assisted answering on the same prompts.
5. Refine traces and prompt instructions based on observed failures.

## Evaluation Criteria

A first working version should be judged on:

- choosing tools only when needed
- returning correct answers on basic tasks
- handling tool failure gracefully
- keeping the action loop understandable
- avoiding fake or hallucinated tool outputs

## Failure Modes To Watch

Typical early failure modes for this project include:

- calling a tool unnecessarily when the answer is already trivial
- skipping a tool and hallucinating the result
- misreading tool output and propagating the error
- looping too long without improving the answer
- returning a correct intermediate observation but a weak final answer

## Possible Future Extensions

Once the base loop is stable, useful follow-ups include:

- structured tool schemas
- tool retry policy
- conversation state
- better tracing and observability
- prompt variants for tool selection strategy

## Why This Project Matters

This project is small by design, but it establishes the baseline for everything that follows:

- tool use becomes easier to evaluate once the loop is explicit
- later work on memory and planning is easier to reason about with a simple baseline
- multi-agent patterns are easier to compare against a clear single-agent starting point

A strong implementation here makes the later projects easier to understand and evaluate.
