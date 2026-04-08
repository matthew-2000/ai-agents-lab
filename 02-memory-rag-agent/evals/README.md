# Evals

Keep evals lightweight and local.

The current cases cover:

- explicit user fact recall
- short conversational continuity
- preference retention across turns
- retrieval triggering for external-knowledge questions
- chunk-level retrieval and citation validation on grounded answers
- retrieval skipping for memory-only questions
- conflict handling when a user updates previously stored facts
- safe clarification behavior for ambiguous prompts
- understandable failure cases when phrasing falls outside the extractor or heuristics

The expected behavior is written in plain language in `test_cases.json`.

Run the live eval suite with:

`python3 src/main.py --run-evals`

The structured fields in each case are intentionally lightweight:

- `required_substrings`
- `forbidden_substrings`
- `expect_retrieval_used`
- `expect_response_origin`
- `expect_citation_validation`
