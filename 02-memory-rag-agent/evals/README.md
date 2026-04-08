# Evals

Keep evals lightweight and local.

The current cases cover:

- explicit user fact recall
- short conversational continuity
- preference retention across turns
- retrieval triggering for external-knowledge questions
- retrieval skipping for memory-only questions
- conflict handling when a user updates previously stored facts
- safe clarification behavior for ambiguous prompts
- understandable failure cases when phrasing falls outside the extractor or heuristics

The expected behavior is written in plain language in `test_cases.json`.
