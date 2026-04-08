# 02 - Memory + RAG Agent

## Status

Sprint 3 implemented.

This project is intentionally standalone. It can be moved out of this repository without
depending on code from `01-tool-using-assistant` or any other folder.

## Objective

Build an assistant that can retain short-term conversation state and retrieve relevant
external context when needed.

## Main Concept

This project extends the baseline single-agent setup by adding explicit short-term memory.
The agent should remember user facts and preferences across a short conversation without
mixing that recalled context into the raw current input.

Sprint 1 established the standalone runtime and short-term memory layer.
Sprint 2 wired local retrieval into the answer flow with deterministic gating.
Sprint 3 adds robustness: memory conflict tracking, safer fallback behavior when grounding is
missing, and explicit warnings for ambiguous or weakly supported turns.

## Current Scope

- Keep the interaction single-agent and text-only.
- Support a short conversation with explicit memory of prior user facts or preferences.
- Keep memory separate from the current user message in the internal flow.
- Retrieve passages from a small local knowledge base when the query needs external context.
- Show which retrieved snippets were used in the final answer.
- Track updated memory facts such as changed location or role.
- Fail safely when the query is too ambiguous or the local KB cannot ground the answer.
- Provide a standalone CLI and local self-checks.

## Expected Architecture

- one LLM-powered agent
- standalone OpenAI client and CLI runtime inside this folder
- deterministic short-term memory store
- explicit memory extraction from user turns
- recent-turn history kept separately from extracted memory facts
- memory conflict tracking for updated user facts
- deterministic retrieval decision layer
- local retrieval module and local knowledge base
- local guardrail-style fallbacks for ambiguous or weakly grounded turns
- lightweight JSONL trace logs

## Directory Structure

```text
02-memory-rag-agent/
├── README.md
├── requirements.txt
├── .env.example
├── src/
│   ├── agent.py
│   ├── cli.py
│   ├── config.py
│   ├── main.py
│   ├── memory.py
│   └── retrieval.py
├── data/
│   ├── knowledge_base.json
│   └── prompt_examples.json
├── evals/
│   ├── README.md
│   └── test_cases.json
├── logs/
│   └── .gitkeep
└── notes.md
```

## Running The Project

1. Install dependencies: `python3 -m pip install -r requirements.txt`
2. Copy `.env.example` to `.env` and set `OPENAI_API_KEY`
3. Run local checks: `python3 src/main.py --self-check`
4. Start the interactive CLI: `python3 src/main.py`

## Interactive CLI

Available commands inside the CLI:

- `/help` shows the available commands
- `/examples` lists the bundled example prompts
- `/example <id>` injects one bundled prompt into the current conversation
- `/memory` shows the current memory snapshot
- `/retrieve <query>` previews the retrieval decision and matched snippets
- `/reset` clears the current conversation memory
- `/self-check` runs local deterministic checks
- `/exit` closes the CLI

For non-interactive smoke tests you can also pass repeated `--prompt` flags to keep one session:

`python3 src/main.py --prompt "My name is Matteo." --prompt "What is my name?"`

Any line that does not start with `/` is treated as a normal user prompt.

## Sprint 1, 2, And 3 Deliverables

- standalone project scaffold
- short-term memory store for user facts and preferences
- conversation session that preserves memory across turns
- local retrieval module with a small knowledge base
- deterministic retrieval gating for each turn
- final answers that surface the retrieved snippets used
- warnings and local fallback responses for ambiguous or weakly grounded turns
- explicit tracking of updated memory values
- eval and prompt-example assets for further iteration

## Not Yet In Scope

- vector search or embeddings
- long-term memory
- planning or multi-agent behavior

## Evaluation Criteria

The current version should be judged on:

- whether the agent recalls short-term user facts across turns
- whether memory stays separate from the raw current input
- whether retrieval is triggered when external knowledge is needed and skipped for memory-only turns
- whether retrieved snippets remain visible in the final answer
- whether changed user facts are surfaced as updates instead of being silently overwritten
- whether ambiguous or weakly grounded turns fail safely
- whether the project is runnable on its own
- whether failure cases are inspectable via traces and local checks

## Failure Modes To Watch

- the memory extractor misses a user fact because phrasing is unexpected
- a generic statement is stored as a user preference when it should not be
- the agent over-relies on recent turns instead of extracted memory
- memory conflicts are still heuristic and only cover a small set of fact types
- retrieval is triggered on a vague query with only weak keyword overlap
- retrieval is skipped when a knowledge-seeking query uses phrasing outside the current heuristics

## Possible Next Step

Useful follow-ups would be better semantic retrieval, richer ambiguity detection, and more
explicit attribution between the final answer text and each retrieved snippet.
