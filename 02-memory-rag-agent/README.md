# 02 - Memory + RAG Agent

A standalone, portfolio-ready example of a memory-aware RAG assistant.

This project combines:

- short-term conversational memory
- chunked local retrieval over a knowledge base
- inline chunk citations for grounded answers
- safe fallback behavior on ambiguity or missing evidence
- a runnable eval suite for regression checks

It is intentionally self-contained. The folder can be moved out of this repository without
depending on code from any other project.

## Why This Project Matters

Many RAG demos stop at “retrieve a blob and answer with it.” This project goes further while
staying compact enough to study:

- it separates user memory from retrieved knowledge
- it retrieves chunk-level passages instead of whole opaque documents
- it asks the model to cite retrieved chunk ids inline
- it validates that cited chunk ids actually came from the retrieved set
- it fails safely when the prompt is ambiguous or the local KB cannot support the answer

That makes it a much stronger teaching example than a toy keyword-search wrapper, while still
being small enough to understand end to end.

## Current State

The current version includes the work from the first three implementation sprints plus a final
RAG quality pass:

- Sprint 1: standalone runtime and short-term memory
- Sprint 2: retrieval integrated into the answer path
- Sprint 3: robustness, memory conflict handling, and safer fallbacks
- Final polish: chunked retrieval, stronger scoring, inline citations, citation validation, and
  a cleaner presentation layer

## What It Demonstrates

- Memory recall: remembers user facts such as name, preferences, or updated location
- Context separation: keeps conversation memory separate from external retrieved evidence
- Grounded retrieval: answers knowledge questions using retrieved chunks from a local KB
- Citation discipline: includes inline citations like `[kb-005#chunk-01]`
- Safety behavior: asks for clarification or abstains when grounding is weak
- Regression readiness: runs a repeatable eval suite against the live model

## Architecture

High-level flow:

1. The user sends a turn.
2. The memory store extracts explicit user facts and preserves recent turns.
3. The retrieval layer decides whether external knowledge is needed.
4. If needed, it ranks chunked passages from the local KB.
5. The model receives three clearly separated inputs:
   current prompt, conversation memory, retrieved context.
6. The answer is returned with inline citations when retrieval is used.
7. The runtime validates cited chunk ids and logs the turn.

Core components:

- one LLM-powered assistant
- deterministic short-term memory store
- deterministic retrieval gating
- chunked local retriever with hybrid lexical scoring
- local guardrail-style fallback responses
- JSONL trace logging
- live eval runner

## Retrieval Design

This is not just whole-document lookup.

- Source documents are split into overlapping sentence-window chunks
- Retrieval scores combine body overlap, title overlap, tag overlap, and phrase bonuses
- The system limits over-concentration from a single source by capping per-source chunk selection
- The generator sees chunk ids and is instructed to cite them inline
- The runtime checks that cited chunk ids belong to the retrieved set

Current tradeoff:

- The retriever is still lexical, not embedding-based
- That keeps the project lightweight and inspectable, but paraphrase recall can still be improved

## Project Structure

```text
02-memory-rag-agent/
├── README.md
├── requirements.txt
├── .env.example
├── src/
│   ├── agent.py
│   ├── cli.py
│   ├── config.py
│   ├── eval_runner.py
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

## Quickstart

From [02-memory-rag-agent](/ai-agents-lab/02-memory-rag-agent):

1. Install dependencies:
   `python3 -m pip install -r requirements.txt`
2. Copy `.env.example` to `.env` and set `OPENAI_API_KEY`
3. Run local checks:
   `python3 src/main.py --self-check`
4. Start the CLI:
   `python3 src/main.py`

Useful non-interactive commands:

- `python3 src/main.py --prompt "My name is Matteo." --prompt "What is my name?"`
- `python3 src/main.py --prompt "Explain retrieval augmented generation."`
- `python3 src/main.py --prompt "What is the difference between sparse and dense retrieval?"`
- `python3 src/main.py --run-evals`

## Demo Flow

If you want to present this project quickly, this sequence works well in under two minutes.

### 1. Memory

```bash
python3 src/main.py --prompt "My name is Matteo." --prompt "What is my name?"
```

What it shows:

- short-term conversational memory
- no retrieval for a memory-only question

### 2. Grounded RAG

```bash
python3 src/main.py --prompt "Explain retrieval augmented generation."
```

What it shows:

- retrieval is triggered
- the answer includes inline chunk citations
- the runtime exposes the retrieved chunks used

### 3. Better Retrieval Question

```bash
python3 src/main.py --prompt "What is the difference between sparse and dense retrieval?"
```

What it shows:

- chunked retrieval on a more specific topic
- multiple grounded citations across the answer

### 4. Robustness

```bash
python3 src/main.py --prompt "I live in Rome." --prompt "I moved to Milan." --prompt "Where do I live?"
python3 src/main.py --prompt "Which one is better?"
```

What it shows:

- memory conflict handling
- clarification instead of guessing on ambiguous prompts

## CLI Commands

- `/help` shows the available commands
- `/examples` lists bundled prompts
- `/example <id>` injects one bundled prompt into the current session
- `/memory` prints the current memory snapshot
- `/retrieve <query>` previews retrieval without calling the model
- `/run-evals` runs the live eval suite
- `/reset` clears the session memory
- `/self-check` runs deterministic local checks
- `/exit` closes the CLI

## Evaluation

The project includes both quick checks and live evals.

Local checks:

- `python3 src/main.py --self-check`
- `python3 -m py_compile src/*.py`

Live eval suite:

- `python3 src/main.py --run-evals`

The eval suite currently checks:

- memory recall
- retrieval triggering and retrieval skipping
- citation validation
- memory conflict handling
- ambiguous prompt handling
- safe behavior when the KB lacks grounding

## What Makes It Strong

For a compact project, this is already a serious RAG example because it covers:

- retrieval quality at the passage level
- grounding and inspectability
- distinction between memory and knowledge
- safety behavior under uncertainty
- repeatable evaluation

## Honest Limitations

This is strong, but not “final-form production RAG.”

- retrieval is lexical rather than embedding-based
- citation validation checks membership, not full claim-level attribution
- memory extraction is still rule-based and narrow by design
- there is no reranker yet
- the KB is richer than before, but still intentionally small

## Best Next Steps

If you want to push it further, the highest-value upgrades would be:

- embeddings-based or hybrid semantic retrieval
- a reranker stage
- stronger claim-to-citation attribution
- unit tests for memory, retrieval, and citation validation
- a larger domain-specific knowledge base
