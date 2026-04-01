# ai-agents-lab

`ai-agents-lab` is a public portfolio repository for a progressive series of AI agent projects.
It is designed as a curated engineering lab: each project explores a distinct agent pattern, while the repository root acts as the index, documentation layer, and public-facing showcase.

This repository is intentionally **not** a monolithic codebase and **not** a shared framework. Each project lives in its own directory, owns its own dependencies, and can evolve independently.

## Purpose

This repository serves three goals at once:

- support progressive development of AI agent projects
- work as a strong public GitHub portfolio
- provide a credible technical narrative for CV, interviews, and technical discussions

The progression starts with basic tool-using agents and moves toward memory, planning, coordination, reflection, guardrails, and research-oriented multi-agent systems.

## Repository Overview

| Project | Focus | Approx. difficulty |
| --- | --- | --- |
| `01-tool-using-assistant` | Basic agent loop, tool calling, simple ReAct pattern | Beginner |
| `02-memory-rag-agent` | Memory, retrieval, contextual recall, simple RAG | Beginner to intermediate |
| `03-planner-executor-agent` | Task decomposition and plan/execution split | Intermediate |
| `04-travel-planner-agent` | Constraint-aware planning with budget, time, and interests | Intermediate |
| `05-manager-multi-agent` | Manager pattern coordinating specialist agents | Intermediate |
| `06-decentralized-multi-agent` | Peer-to-peer handoffs between specialized agents | Intermediate to advanced |
| `07-reflexion-coding-agent` | Self-critique, test feedback loops, iterative improvement | Advanced |
| `08-guardrails-hitl-agent` | Guardrails, approvals, human-in-the-loop controls | Advanced |
| `09-research-multi-agent-system` | Research synthesis, critique, and hypothesis generation | Advanced |

## What Each Project Teaches

1. `01-tool-using-assistant`: how to build a minimal agent loop with tool calls.
2. `02-memory-rag-agent`: how to add memory and retrieval without overengineering.
3. `03-planner-executor-agent`: how to separate planning from execution for multi-step tasks.
4. `04-travel-planner-agent`: how to apply planning patterns to a realistic constrained domain.
5. `05-manager-multi-agent`: how to coordinate specialist agents under a manager.
6. `06-decentralized-multi-agent`: how to design handoffs without a central orchestrator.
7. `07-reflexion-coding-agent`: how to use feedback loops to improve outputs iteratively.
8. `08-guardrails-hitl-agent`: how to add risk controls and approval points.
9. `09-research-multi-agent-system`: how to combine multiple roles into a portfolio-level capstone.

## Repository Design Principles

- **Single repository, multiple independent projects**: one GitHub home for the full learning path.
- **No shared code layer**: no `common/`, `shared/`, `core/`, or reusable package across projects.
- **Project autonomy first**: each project should be understandable and evolvable on its own.
- **Root as portfolio index**: the root explains, curates, and connects the work.
- **Minimal scaffolding**: only enough boilerplate to start building immediately.
- **Evaluation-oriented thinking**: each project includes a place for simple evals and failure analysis.

## Why A Single Repository?

A single repository makes the overall journey easier to understand from the outside.
For recruiters, engineers, and researchers, it provides:

- a visible progression from foundational patterns to more advanced systems
- a single canonical place to browse design choices and maturity
- a compact portfolio artifact that is easy to link from a CV or profile
- a coherent narrative without forcing unrelated projects into one codebase

## Project Independence

Each project in this repository is intentionally independent.

- No Python package is shared between projects.
- No imports should cross project boundaries.
- No hidden internal framework is assumed.
- Dependencies are local to each project.
- Any project could later be extracted into its own repository with minimal friction.

This is deliberate: the goal is to show architectural judgment, not to force reuse where reuse would blur project boundaries.

## How To Navigate The Repository

- Start from this root `README.md` for the overall map.
- Use `docs/roadmap.md` for the progressive learning path.
- Use `docs/evaluation-guidelines.md` for a lightweight evaluation mindset.
- Open any project folder for its dedicated scope, notes, and local scaffold.
- Use `docs/project-template.md` when adding future projects in the same style.

## Suggested Development Order

1. `01-tool-using-assistant`
2. `02-memory-rag-agent`
3. `03-planner-executor-agent`
4. `04-travel-planner-agent`
5. `05-manager-multi-agent`
6. `06-decentralized-multi-agent`
7. `07-reflexion-coding-agent`
8. `08-guardrails-hitl-agent`
9. `09-research-multi-agent-system`

This order keeps the learning curve controlled: first agent loops, then state and retrieval, then planning, then coordination, then safety and higher-order reasoning.

## Evaluation Mindset

Each project should eventually be judged on:

- output correctness for its intended scope
- appropriateness of tool usage
- adherence to explicit constraints
- robustness under ambiguity and missing information
- visibility of failure cases and design limitations

The goal is not heavyweight infrastructure on day one, but the habit of testing claims against concrete scenarios.

## Learning Roadmap

- **Stage 1: Single-agent fundamentals**
  Build a basic tool-using agent and then add memory and retrieval.
- **Stage 2: Structured reasoning**
  Introduce planning and explicit decomposition for multi-step tasks.
- **Stage 3: Domain-constrained application**
  Apply those patterns to a realistic travel planning workflow.
- **Stage 4: Coordination**
  Compare centralized management with decentralized handoff patterns.
- **Stage 5: Reliability and safety**
  Add critique loops, tests, guardrails, and human approvals.
- **Stage 6: Portfolio capstone**
  Combine multiple ideas into a research-oriented multi-agent system.

## Future Work

- deepen each scaffold into a fully implemented standalone project
- add lightweight demos, evaluation datasets, and architecture diagrams
- document tradeoffs between agent patterns as the projects mature
- compare implementation styles across different model providers or tool stacks
- add retrospective notes on what scales well and what does not

## What This Repository Is Not

- It is **not** a single agent framework.
- It is **not** a shared internal library.
- It is **not** a monolithic codebase with tightly coupled modules.
- It is **not** a reuse-first monorepo.

It is a lab and portfolio repository for a set of intentionally independent AI agent projects collected under one coherent public narrative.
