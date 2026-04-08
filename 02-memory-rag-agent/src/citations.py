"""Citation helpers for grounded answers."""

from __future__ import annotations

import re

from documents import RetrievedSnippet


def extract_chunk_citations(text: str) -> list[str]:
    """Extract inline chunk citations such as [kb-002#chunk-01]."""

    citations = re.findall(r"\[([a-z0-9-]+#chunk-\d{2})\]", text, flags=re.IGNORECASE)
    seen: list[str] = []
    for citation in citations:
        normalized = citation.lower()
        if normalized not in seen:
            seen.append(normalized)
    return seen


def format_sources_appendix(snippets: list[RetrievedSnippet]) -> str:
    """Render a readable sources appendix with metadata."""

    if not snippets:
        return ""

    lines = ["Sources used:"]
    for snippet in snippets:
        location = snippet.section or snippet.metadata.get("file_name") or "local source"
        source_line = f"- {snippet.id}: {snippet.title} | source={snippet.source_type} | location={location}"
        if snippet.url:
            source_line += f" | url={snippet.url}"
        lines.append(source_line)
    return "\n".join(lines)
