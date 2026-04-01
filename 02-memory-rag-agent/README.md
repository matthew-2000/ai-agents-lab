# 02 - Memory + RAG Agent

## Status

Planned.

## Objective

Build an assistant that can retain short-term conversation state and retrieve relevant external context when needed.

## v0 Scope

- Keep the interaction single-agent and text-only.
- Support a short conversation with explicit memory of prior user facts or preferences.
- Retrieve passages from a small local knowledge base instead of answering only from the prompt.
- Keep memory and retrieved context separate in the internal flow.
- Show which retrieved snippets were used in the final answer.
- Stay narrow: no planning, no multi-agent behavior, no long-term production memory.

## Done Criteria

- The agent can answer at least a few multi-turn questions that require recalling earlier context.
- Retrieval is triggered only when external knowledge is actually needed.
- Final answers clearly reflect both conversation memory and retrieved facts when relevant.
- Failure cases such as irrelevant retrieval or forgotten context are documented.
