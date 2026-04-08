# ai-agents-lab

A progressive collection of small AI agent projects, ordered from foundational patterns to more advanced systems.

The sequence starts with simple tool use and moves toward memory, planning, coordination, reflection, guardrails, and research workflows.

## Agent Convention

Unless a project explicitly says otherwise, an "agent" in this repository is assumed to be LLM-powered.

- Agents use an LLM as the decision-making engine for reasoning, tool selection, routing, critique, or response assembly.
- Tools do not need to use an LLM and should often remain deterministic.
- Memory, retrieval, and guardrail components do not need to be LLM-based unless the project specifically benefits from it.
- If a project mixes LLM and non-LLM components, the documentation should state clearly which parts are agents and which parts are supporting infrastructure.

## Roadmap

| Project | Focus | Difficulty | Status |
| --- | --- | --- | --- |
| `01-tool-using-assistant` | Basic agent loop, tool calling, simple ReAct pattern | Beginner | Scaffolded |
| `02-memory-rag-agent` | Memory, retrieval, contextual recall, grounded RAG with source sync | Beginner to intermediate | Implemented |
| `03-planner-executor-agent` | Task decomposition and plan/execution split | Intermediate | Planned |
| `04-travel-planner-agent` | Constraint-aware planning with budget, time, and interests | Intermediate | Planned |
| `05-manager-multi-agent` | Manager pattern coordinating specialist agents | Intermediate | Planned |
| `06-decentralized-multi-agent` | Peer-to-peer handoffs between specialized agents | Intermediate to advanced | Planned |
| `07-reflexion-coding-agent` | Self-critique, test feedback loops, iterative improvement | Advanced | Planned |
| `08-guardrails-hitl-agent` | Guardrails, approvals, human-in-the-loop controls | Advanced | Planned |
| `09-research-multi-agent-system` | Research synthesis, critique, and hypothesis generation | Advanced | Planned |

## What This Repository Covers

1. `01-tool-using-assistant`: building a minimal agent loop with tool calls.
2. `02-memory-rag-agent`: adding memory and retrieval without overengineering.
3. `03-planner-executor-agent`: separating planning from execution for multi-step tasks.
4. `04-travel-planner-agent`: applying planning patterns to a constrained real-world domain.
5. `05-manager-multi-agent`: coordinating specialist agents under a manager.
6. `06-decentralized-multi-agent`: designing handoffs without a central orchestrator.
7. `07-reflexion-coding-agent`: using feedback loops to improve outputs iteratively.
8. `08-guardrails-hitl-agent`: introducing approval points and explicit safety controls.
9. `09-research-multi-agent-system`: combining multiple roles into a research-oriented capstone.

## Current State

The repository currently contains:

- the initial scaffold for `01-tool-using-assistant`
- an implemented `02-memory-rag-agent` with memory, hybrid retrieval, citations, and trusted source sync
- planned stubs for `03` through `09`
- shared documentation used to keep the sequence consistent as the projects evolve

## How To Read It

- Start here for the overall sequence.
- Use `docs/roadmap.md` for the staged learning path.
- Use `docs/evaluation-guidelines.md` for the evaluation criteria shared across projects.
- Open each project folder for its own scope, notes, and implementation.
- Use `docs/project-template.md` when adding a new project in the same style.

## Development Order

1. `01-tool-using-assistant`
2. `02-memory-rag-agent`
3. `03-planner-executor-agent`
4. `04-travel-planner-agent`
5. `05-manager-multi-agent`
6. `06-decentralized-multi-agent`
7. `07-reflexion-coding-agent`
8. `08-guardrails-hitl-agent`
9. `09-research-multi-agent-system`

## Evaluation

Each project should eventually be judged on:

- output correctness for its intended scope
- appropriateness of tool usage
- adherence to explicit constraints
- robustness under ambiguity and missing information
- visibility of failure cases and design limitations

The aim is to keep evaluation lightweight but concrete from the start.

At the repository level, `02-memory-rag-agent` now sets the quality bar for later projects by
showing:

- clear separation between agent behavior and deterministic support systems
- eval-backed iteration instead of prompt-only tuning
- inspectable retrieval with citations and readable sources
- a local-first architecture with optional trusted online sync instead of uncontrolled live web access

## Future Additions

- complete the planned project directories as their scope solidifies
- add lightweight demos, diagrams, and evaluation assets
- document tradeoffs between agent patterns as the projects mature
- capture lessons learned after each implementation milestone
