# 09 - Research Multi-Agent System

## Status

Planned.

## Objective

Build a research-oriented multi-agent system that can read, synthesize, critique, and combine evidence into a final output.

## v0 Scope

- Use a small set of roles such as reader, synthesizer, critic, and final writer.
- Work on bounded research questions that can be handled with a small source set.
- Keep evidence traceability explicit from source extraction to final synthesis.
- Include a critique step that challenges weak claims or unsupported conclusions.
- Produce a final answer that distinguishes evidence, inference, and uncertainty.
- Keep the capstone small enough to remain inspectable rather than broad and autonomous.

## Done Criteria

- The final output cites or references the evidence actually used in the synthesis.
- Critique materially improves unsupported or weak intermediate conclusions.
- The system handles uncertainty explicitly instead of overstating confidence.
- The project includes eval scenarios for both clean evidence sets and conflicting sources.
