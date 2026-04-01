# Roadmap

This repository follows a progressive path from simple single-agent systems to more advanced multi-agent and safety-aware designs.

## Stage 1: Single-Agent Foundations

### 01. Tool-Using Assistant

- build a minimal agent loop
- add simple tool invocation
- establish a clear observe, reason, act cycle

### 02. Memory + RAG Agent

- add short-term conversational memory
- introduce retrieval over external knowledge
- separate recalled context from current input

## Stage 2: Structured Reasoning

### 03. Planner-Executor Agent

- split planning from execution
- make intermediate steps explicit
- improve reliability on multi-step work

### 04. Travel Planner Agent

- plan under budget, timing, and preference constraints
- keep scope to travel planning rather than real booking automation
- practice explicit assumptions and tradeoff handling

## Stage 3: Multi-Agent Coordination

### 05. Manager Multi-Agent

- coordinate specialists through a manager
- compare orchestration benefits against simpler baselines
- keep role boundaries explicit

### 06. Decentralized Multi-Agent

- explore peer handoffs
- model ownership transfer and escalation
- study coordination without a single central controller

## Stage 4: Reliability And Control

### 07. Reflexion Coding Agent

- add self-critique and revision loops
- use tests or feedback as grounding signals
- study when reflection helps and when it causes drift

### 08. Guardrails + HITL Agent

- introduce policy checks and approval gates
- make risky actions auditable and reviewable
- design systems that fail safely under uncertainty

## Stage 5: Capstone System

### 09. Research Multi-Agent System

- combine reading, synthesis, critique, and hypothesis generation
- build a portfolio-level capstone system
- focus on evidence handling and traceability

## Suggested Execution Strategy

- complete the projects in order when possible
- keep each implementation intentionally narrow
- document failure modes early instead of hiding them
- prefer simple evals over large infrastructure
- extract lessons after each project before moving to the next one
