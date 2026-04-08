# Notes

## Current Status

- A working v1 agent loop is implemented with the OpenAI Responses API.
- The current toolset is intentionally small: calculator, live weather with fallback, and local knowledge-base search.
- This project is intentionally independent from the other folders in the repository.

## Design Decisions

- Keep scope narrow and realistic.
- Avoid imports from sibling projects.
- Prefer simple, inspectable components over premature abstractions.
- Keep tools deterministic so tool selection remains the main behavior under evaluation.
- Use a live weather integration where it adds realism, but keep local fallback data so the demo remains robust and inspectable.

## Open Questions

- Which other mocked components should graduate to live external services after weather?
- How much trace detail is useful before the logs become noisy?
- Should a future iteration add a lightweight automated eval runner around `test_cases.json`?

## Next Steps

- Add a small automated eval harness over the existing test cases.
- Compare prompt variants for tool selection and final answer quality.
- Record concrete failure patterns after a few real prompts and tool errors.

## Failure Cases Observed

- None documented yet after implementation. Capture tool misuse, looping, or weak answer synthesis here as they appear.
