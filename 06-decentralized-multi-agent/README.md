# 06 - Decentralized Multi-Agent

## Status

Planned.

## Objective

Build a multi-agent system where specialists can hand work off to each other without a single central manager.

## v0 Scope

- Define a small group of specialist agents with explicit ownership boundaries.
- Allow agents to transfer work directly when another role is better suited to the subtask.
- Make handoff reasons visible so routing decisions can be inspected later.
- Keep the communication pattern simple enough to avoid uncontrolled loops.
- Use a bounded task where ownership transfer is realistic and useful.
- Exclude large-scale autonomy, open-ended conversation, or production reliability concerns from v0.

## Done Criteria

- Agents hand work off for clear role-based reasons rather than arbitrarily.
- The system reaches a final answer without excessive bouncing between agents.
- Handoff traces make it possible to understand where coordination broke down.
- Evals include both good transfers and failure cases such as redundant or circular handoffs.
