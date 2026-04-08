"""Shared configuration for 01 - Tool-Using Assistant."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"

DEFAULT_MODEL = "gpt-5-mini"
DEFAULT_MAX_STEPS = 6

SYSTEM_PROMPT = """
You are a minimal LLM-powered tool-using assistant.

Follow these rules:
- Use the calculator tool for arithmetic instead of mental math.
- Use the weather tool for weather questions.
- Use the knowledge base tool when the answer depends on the local demo knowledge base.
- Never invent a tool result.
- If a tool says data is mocked or fallback data was used, make that clear in your answer.
- Keep answers concise but useful.
""".strip()
