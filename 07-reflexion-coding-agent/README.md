# 07 - Reflexion Coding Agent

## Status

Planned.

## Objective

Build a coding-oriented agent that improves its output by critiquing failed attempts and revising against feedback.

## v0 Scope

- Start from a narrow coding task with runnable tests or deterministic checks.
- Produce an initial solution, run feedback, and allow one or more revision loops.
- Use test results or structured critique as the grounding signal for revision.
- Keep the revision trace visible so changes can be connected to specific failures.
- Stop after a bounded number of attempts rather than looping indefinitely.
- Avoid broad autonomous repo editing or complex planning beyond what the task requires.

## Done Criteria

- The agent improves at least some failing attempts after receiving concrete feedback.
- Revisions respond to the observed failure instead of drifting into unrelated changes.
- The stopping condition is explicit and prevents unbounded retry loops.
- The project compares first-pass performance versus revised performance on a small eval set.
