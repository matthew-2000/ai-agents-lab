# 03 - Planner-Executor Agent

## Status

Planned.

## Objective

Build an agent that separates task decomposition from task execution for multi-step requests.

## v0 Scope

- Split the workflow into two explicit phases: planning first, execution second.
- Accept tasks that are too large for a single direct answer but still narrow enough to stay deterministic.
- Produce a short step-by-step plan before any execution begins.
- Execute each step with simple tools or direct reasoning, then assemble the result.
- Keep plan updates visible when execution reveals missing information.
- Avoid multi-agent coordination, reflection loops, or advanced memory in v0.

## Done Criteria

- The system produces a coherent plan for representative multi-step inputs.
- Execution follows the plan closely and only revises it when there is a clear reason.
- Intermediate outputs make it easy to inspect where a failure happened.
- The project includes evals for both successful plans and broken or incomplete plans.
