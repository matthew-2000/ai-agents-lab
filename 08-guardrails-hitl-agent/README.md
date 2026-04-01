# 08 - Guardrails + HITL Agent

## Status

Planned.

## Objective

Build an agent with explicit policy checks and human approval points for risky or uncertain actions.

## v0 Scope

- Define a narrow task domain with a few clearly disallowed or high-risk actions.
- Add a guardrail layer that can block, allow, or escalate actions for review.
- Require human confirmation before simulated risky operations continue.
- Keep decisions auditable with simple logs or structured traces.
- Include both straightforward safe requests and ambiguous requests that should trigger review.
- Exclude real-world side effects and keep the environment fully simulated in v0.

## Done Criteria

- The system reliably blocks or escalates actions that violate the declared policy.
- Safe requests pass through without unnecessary friction.
- Approval checkpoints are visible and easy to inspect after the run.
- Evals cover policy violations, ambiguous inputs, and safe allowed cases.
