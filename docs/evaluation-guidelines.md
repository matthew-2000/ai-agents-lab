# Evaluation Guidelines

The goal of evaluation in this repository is not to create heavyweight benchmark infrastructure from the start.
The goal is to make each project falsifiable with a small set of realistic scenarios.

## Core Evaluation Dimensions

### Correctness

Check whether the agent produces an output that is materially correct for the task.

Questions to ask:

- Did it solve the intended problem?
- Did it preserve important details?
- Did it hallucinate missing facts or steps?

### Appropriate Tool Usage

Check whether the agent uses tools when needed and avoids them when not needed.

Questions to ask:

- Did it select the right tool for the subtask?
- Did it misuse a tool or overuse tools unnecessarily?
- Did tool outputs materially improve the answer?

### Constraint Adherence

Check whether the agent respects explicit boundaries.

Examples:

- budget limits
- safety rules
- approval requirements
- scope limits such as planning only or no real booking

### Robustness On Ambiguous Input

Check how the agent behaves when instructions are incomplete, vague, or conflicting.

Questions to ask:

- Does it ask for clarification when needed?
- Does it make reasonable assumptions and state them clearly?
- Does it fail safely when ambiguity matters?

### Failure Cases

Document failure cases explicitly instead of treating them as exceptions to ignore.

Capture:

- the input pattern that caused failure
- the observed behavior
- the likely root cause
- the possible mitigation

## Lightweight Evaluation Practice

For each project:

- start with a small `test_cases.json`
- include both normal and edge cases
- write expected behavior in plain language
- keep evaluation simple enough to run often

## Recommended Minimum Bar

Before calling a project working, it should:

- succeed on a few representative happy-path cases
- fail in understandable ways on difficult cases
- show at least basic evidence that constraints are enforced
- have documented next steps for reliability improvements
