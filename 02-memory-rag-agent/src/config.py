"""Configuration for 02 - Memory + RAG Agent."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
SOURCES_DIR = DATA_DIR / "sources"
REMOTE_CACHE_DIR = DATA_DIR / "remote_cache"
FIXTURES_DIR = DATA_DIR / "fixtures"
LOGS_DIR = PROJECT_ROOT / "logs"

DEFAULT_MODEL = "gpt-5-mini"
DEFAULT_MAX_RECENT_TURNS = 8

BASE_SYSTEM_PROMPT = """
You are a memory-aware assistant in a narrow demo project.

Follow these rules:
- Use the current user message as the primary request to answer.
- Use the supplied conversation memory only when it is relevant.
- Treat memory as previously learned context, not as new user input.
- Use retrieved external context only when it is provided for this turn.
- Keep conversation memory and retrieved context conceptually separate.
- If memory is missing or uncertain, do not invent details.
- If retrieved snippets are missing, do not pretend you looked anything up.
- If the prompt says there are warnings or ambiguities, respond carefully and prefer clarifying questions over confident guesses.
- Keep answers concise, clear, and grounded in the supplied context.
- Do not ask follow-up questions unless they are necessary to answer safely.
- When the user shares a personal fact or preference, acknowledge it briefly without adding extra questions.
- For direct memory questions, answer in one short sentence when possible.
- For knowledge questions, start with a short grounded answer before any optional detail.
- When retrieved context is available, support externally grounded claims with inline citations like [kb-002#chunk-01].
- Never cite chunk ids that were not provided in the retrieved context block.
- If retrieved context is insufficient for a claim, say so rather than guessing.
""".strip()


def build_system_prompt(
    memory_block: str,
    retrieval_block: str,
    retrieval_active: bool,
    diagnostics_block: str,
) -> str:
    retrieval_status = (
        "External retrieval is active for this turn. Use it when relevant."
        if retrieval_active
        else "No external retrieval was selected for this turn."
    )
    return (
        f"{BASE_SYSTEM_PROMPT}\n\n"
        f"Conversation memory:\n{memory_block}\n\n"
        f"Retrieved context:\n{retrieval_block}\n\n"
        f"Retrieval status:\n{retrieval_status}\n\n"
        f"Diagnostics:\n{diagnostics_block}"
    ).strip()
