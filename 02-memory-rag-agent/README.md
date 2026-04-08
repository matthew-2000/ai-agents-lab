# 02 - Memory + RAG Agent

A standalone, portfolio-ready example of a memory-aware RAG assistant.

This project combines:

- short-term conversational memory
- local ingestion over a small multi-format knowledge base
- chunked retrieval over normalized source documents
- query analysis with lightweight rewriting and metadata-aware filters
- hybrid local retrieval with reranking
- inline chunk citations for grounded answers
- readable source appendix with source metadata
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

The current version includes the original demo work plus three professionalization sprints:

- Sprint 1: standalone runtime and short-term memory
- Sprint 2: retrieval integrated into the answer path
- Sprint 3: robustness, memory conflict handling, and safer fallbacks
- Sprint 1 professionalization pass: canonical source documents, local ingestion, richer chunk
  metadata, readable source appendix, and stronger retrieval traces
- Sprint 2 professionalization pass: query analysis, hybrid retrieval, reranking, deduplication,
  and smarter filtering
- Sprint 3 professionalization pass: trusted online source sync, governance rules, incremental
  caching, and refreshable remote documents

## What It Demonstrates

- Memory recall: remembers user facts such as name, preferences, or updated location
- Context separation: keeps conversation memory separate from external retrieved evidence
- Grounded retrieval: answers knowledge questions using retrieved chunks from normalized sources
- Query routing: distinguishes memory questions from knowledge, comparison, and navigational
  retrieval prompts
- Citation discipline: includes inline citations like `[kb-005#chunk-01]`
- Source visibility: appends readable source metadata after grounded answers
- Trusted source sync: can ingest approved web pages into the local retrieval corpus
- Safety behavior: asks for clarification or abstains when grounding is weak
- Regression readiness: runs a repeatable eval suite against the live model

## Architecture

High-level flow:

1. The user sends a turn.
2. The memory store extracts explicit user facts and preserves recent turns.
3. The retrieval layer classifies the query and decides whether external knowledge is needed.
4. If needed, it rewrites the query, applies metadata filters, and ranks chunked passages from the
   normalized local corpus.
5. Trusted online sources can be synced into a local cache and merged into the retrievable corpus.
6. The model receives three clearly separated inputs:
   current prompt, conversation memory, retrieved context.
7. The answer is returned with inline citations when retrieval is used.
8. The runtime validates cited chunk ids and logs the turn.

Core components:

- one LLM-powered assistant
- deterministic short-term memory store
- local ingestion pipeline for `json`, `md`, `txt`, `html`, and optional `pdf`
- canonical source document schema with metadata
- trusted source catalog and domain governance rules
- incremental remote sync cache
- deterministic retrieval gating
- query analyzer with lightweight rewriting and metadata filters
- chunked local retriever with hybrid lexical plus semantic-lite scoring
- local reranking and deduplication layer
- local guardrail-style fallback responses
- JSONL trace logging
- live eval runner

## Retrieval Design

This is not just whole-document lookup.

- Local files are ingested into a canonical document format with metadata such as source type,
  section, language, trust score, and optional URL
- Source documents are split into overlapping sentence-window chunks
- Query analysis expands some retrieval phrases, identifies broad query type, and extracts simple
  metadata filters
- Retrieval scores combine body overlap, title overlap, tag overlap, section overlap, phrase
  bonuses, semantic-lite overlap, and a small trust-weight bonus
- A reranking pass rewards coverage and title alignment before the final context is packed
- The system limits over-concentration from a single source by capping per-document chunk selection
- The generator sees chunk ids and is instructed to cite them inline
- The runtime checks that cited chunk ids belong to the retrieved set
- The final answer includes a readable appendix listing the retrieved sources used
- Approved web sources can be fetched, normalized, and cached locally with domain-level governance
- Incremental sync skips unchanged pages using content hashes

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
│   ├── citations.py
│   ├── cli.py
│   ├── config.py
│   ├── documents.py
│   ├── eval_runner.py
│   ├── ingestion.py
│   ├── main.py
│   ├── memory.py
│   ├── retrieval.py
│   └── source_sync.py
├── data/
│   ├── fixtures/
│   ├── knowledge_base.json
│   ├── prompt_examples.json
│   ├── remote_cache/
│   └── sources/
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
- `python3 src/main.py --sync-online-sources`
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
- the runtime exposes readable source metadata for the retrieved chunks
- retrieval traces now include score breakdowns that are easier to debug

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

### 5. Trusted Sources

```bash
python3 src/main.py --sync-online-sources
```

What it shows:

- trusted domains are checked before fetch
- synced pages are cached locally for incremental refresh
- remote documents can join the retrieval corpus after sync

## CLI Commands

- `/help` shows the available commands
- `/examples` lists bundled prompts
- `/example <id>` injects one bundled prompt into the current session
- `/memory` prints the current memory snapshot
- `/retrieve <query>` previews retrieval without calling the model
- `/sync` fetches the configured trusted online sources and refreshes the in-memory corpus
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
- comparison-style retrieval with query rewriting
- citation validation
- memory conflict handling
- ambiguous prompt handling
- safe behavior when the KB lacks grounding
- source appendix rendering for grounded responses
- trusted source sync via offline fixtures in self-checks

## What Makes It Strong

For a compact project, this is already a serious RAG example because it covers:

- retrieval quality at the passage level
- source normalization and inspectable metadata
- query analysis before retrieval
- domain governance and incremental remote sync
- grounding and inspectability
- distinction between memory and knowledge
- safety behavior under uncertainty
- repeatable evaluation

## Honest Limitations

This is strong, but not “final-form production RAG.”

- retrieval is still local-first and not yet backed by a true vector index
- citation validation checks membership, not full claim-level attribution
- memory extraction is still rule-based and narrow by design
- semantic matching is heuristic rather than embedding-based
- the local corpus is richer than before, but still intentionally small
- live remote sync depends on network access and the availability of the configured pages

## Best Next Steps

If you want to push it further, the highest-value upgrades would be:

- embedding-based retrieval or a real vector store
- a stronger cross-encoder reranker stage
- stronger claim-to-citation attribution
- unit tests for memory, retrieval, and citation validation
- broader online connectors such as sitemaps, APIs, or knowledge platforms
