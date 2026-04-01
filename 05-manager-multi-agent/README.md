# 05 - Manager Multi-Agent

## Status

Planned.

## Objective

Build a manager-led multi-agent system that coordinates a small set of specialist agents on one task.

## v0 Scope

- Use one manager agent plus a few specialists with sharply defined responsibilities.
- Let the manager decide which specialist to call and in what order.
- Keep handoffs structured so intermediate outputs are easy to inspect.
- Use a task complex enough to justify delegation but small enough to trace end to end.
- Preserve a single final response assembled by the manager.
- Avoid decentralized routing, long autonomy, or excessive role overlap in v0.

## Done Criteria

- The manager delegates work in a way that is materially better than a single flat prompt.
- Specialist outputs stay within their intended role boundaries.
- The final answer integrates specialist contributions without losing consistency.
- The project documents at least a few cases where delegation helps and where it adds overhead.
