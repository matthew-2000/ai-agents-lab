# Notes

## Sprint 1 Decisions

- Keep the project fully standalone even if some implementation ideas mirror project `01`.
- Treat short-term memory as deterministic infrastructure, not as an LLM-driven subsystem.
- Separate memory facts from recent dialogue history so later retrieval can remain a distinct input.
- Keep retrieval code local but disconnected from the answer path until Sprint 2.

## Tradeoffs

- The memory extractor uses lightweight patterns, so recall is intentionally narrow.
- Last-write-wins updates are simple and easy to inspect, but they do not resolve conflicts.
- Recent dialogue is still passed to the model for conversational continuity, so memory is helpful
  but not the only context source.

## Sprint 2 Decisions

- Retrieval triggering is deterministic and heuristic-based rather than model-decided.
- The model sees memory and retrieved snippets in separate prompt blocks.
- Final answers expose retrieved snippet ids and titles through a deterministic appendix.

## Remaining Risks

- The retrieval gate is still keyword-driven and can miss semantically related queries.
- A retrieved snippet listed in the appendix reflects what was supplied to the model, not a
  guaranteed per-sentence attribution.
- The local knowledge base is intentionally tiny, so weak recall can come from sparse content
  rather than only from retrieval logic.

## Sprint 3 Decisions

- Updated memory facts are tracked as conflicts instead of being silently overwritten.
- Ambiguous queries can short-circuit into a local clarification request without calling the model.
- Knowledge-seeking questions with no relevant local snippets now fail safely instead of relying on
  free-form generation.

## Sprint 3 Tradeoffs

- Conflict tracking currently covers only the structured fact fields already extracted.
- The local guardrail responses are intentionally simple and deterministic.
- Some legitimate short questions may be treated as ambiguous until heuristics improve.

## RAG Upgrade Decisions

- Retrieval now runs over chunked source documents instead of whole-document blobs.
- The chunk scorer is a deterministic hybrid lexical ranker with title and tag boosts.
- The generator is instructed to use inline chunk citations, and the runtime validates that
  cited chunk ids belong to the retrieved set.
- A lightweight eval runner is part of the project so retrieval, grounding, and safety behavior
  can be exercised repeatedly.
