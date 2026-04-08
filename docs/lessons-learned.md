# Lessons Learned

Use this document as a running log of what each project taught, where assumptions failed, and which ideas are worth carrying forward.

## Entry Template

### Project

- Name:
- Date:
- Version or milestone:

### What Worked

- 

### What Did Not Work

- 

### Surprising Behaviors

- 

### Failure Cases

- 

### Design Decisions Revisited

- 

### What To Change Next Time

- 

### Open Questions

- 

## Entries

### Project

- Name: `02-memory-rag-agent`
- Date: 2026-04-08
- Version or milestone: Professionalization sprints 1-3

### What Worked

- Keeping memory, retrieval, and guardrail logic separate made the system easier to evolve without
  turning prompt instructions into the only control surface.
- Moving from a demo KB lookup to normalized documents plus readable citations significantly
  improved inspectability.
- Adding query analysis and hybrid local scoring gave a noticeable quality upgrade without
  requiring a full vector infrastructure yet.
- Trusted-source sync kept the architecture professional and auditable while avoiding uncontrolled
  live-web retrieval at answer time.

### What Did Not Work

- Pure lexical retrieval hit a ceiling quickly on paraphrases and comparison-style prompts.
- PDF and remote ingestion depend on environment setup more than the original local-only version.
- Freshness handling is still partial when source metadata is incomplete.

### Surprising Behaviors

- Even small eval suites were enough to expose retrieval regressions early.
- Readable source appendices improved debugging more than internal chunk ids alone.
- A local-first corpus with explicit sync is easier to reason about than live browsing for a
  portfolio-grade RAG system.

### Failure Cases

- Ambiguous prompts still require deterministic fallback logic because retrieval alone cannot
  safely resolve underspecified intent.
- Knowledge queries outside the local or synced corpus still fail closed, which is correct but
  highlights the importance of source coverage.

### Design Decisions Revisited

- Treating retrieval and memory as deterministic infrastructure was the right choice for this
  project stage.
- Starting with one agent and richer tools aligns better with maintainability than prematurely
  introducing multi-agent orchestration.

### What To Change Next Time

- Add a true vector index or embedding-based retrieval layer.
- Introduce stronger output validation and more explicit HITL pathways for higher-risk actions.
- Expand sync from single pages to sitemaps or API-backed connectors.

### Open Questions

- When does this project stop being a RAG assistant and become a workflow agent in the stronger
  sense?
- Which later projects should reuse its evaluation and source-governance patterns at the
  documentation level?

## Notes

- Prefer concrete observations over generic conclusions.
- Record both technical and product-level lessons.
- Capture tradeoffs, not just outcomes.
- Reuse insights at the documentation level, not through shared code between projects.
