# Project Template

Use this template when adding a new project to `ai-agents-lab`.

## Objective

Describe the narrow problem this agent or system is meant to solve.

## Realistic Use Case

Explain a concrete, believable scenario where the project would be useful.

## Architecture

Summarize the intended system design:

- agent roles
- which components are LLM-powered agents
- control flow
- data flow
- tool usage
- memory or state handling

Repository convention:

- Treat every component labeled as an "agent" as LLM-powered unless the project explicitly documents an exception.
- Keep tools, storage, retrieval layers, and guardrails deterministic by default unless there is a clear reason to make them model-driven.

## Tools

List the external tools, APIs, or local utilities the project may use.

## Constraints

Document non-goals and scope boundaries.

Examples:

- no real-world transactions
- no autonomous high-risk actions
- no unnecessary scope expansion

## Evaluation

Define how success should be measured.

- task correctness
- constraint adherence
- tool selection quality
- robustness on imperfect input

## Failure Modes

List the ways the system might fail or misbehave.

## Future Improvements

Capture the most valuable follow-up iterations once the basic version works.
