# Evals

This folder contains lightweight evaluation assets for `01-tool-using-assistant`.
The intent is to keep early testing simple, visible, and easy to extend while the project stays intentionally small.

Suggested usage:

- store representative user prompts or scenarios in `test_cases.json`
- define expected behavior in plain language first
- add edge cases before adding benchmark-heavy infrastructure
- use `python src/main.py --self-check` for local tool sanity checks before running live API calls
- use `python src/main.py --prompt "<prompt>"` for a quick end-to-end manual eval
