"""Local retrieval scaffold for Sprint 2 work."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from config import DATA_DIR


@dataclass(frozen=True)
class KnowledgeBaseEntry:
    """One local document that can be searched deterministically."""

    id: str
    title: str
    text: str
    tags: list[str]


@dataclass(frozen=True)
class RetrievedSnippet:
    """One retrieved snippet passed to the model."""

    id: str
    title: str
    text: str
    tags: list[str]
    score: int


@dataclass(frozen=True)
class RetrievalDecision:
    """Result of deciding whether retrieval should run for a user turn."""

    should_retrieve: bool
    reason: str
    query_type: str
    needs_clarification: bool
    warnings: list[str]
    snippets: list[RetrievedSnippet]


MEMORY_ONLY_PATTERNS = [
    r"\bwhat is my name\b",
    r"\bwhat do you know about me\b",
    r"\bwhat did i say\b",
    r"\bwhat did i tell you\b",
    r"\bwhat do i prefer\b",
    r"\bwhich .* did i say\b",
    r"\brecap what you know about me\b",
    r"\bremember\b",
]

KNOWLEDGE_QUERY_PATTERNS = [
    r"\bwhat is\b",
    r"\bwho is\b",
    r"\bexplain\b",
    r"\btell me about\b",
    r"\bhow does\b",
    r"\bhow do\b",
    r"\bwhy\b",
    r"\bdifference between\b",
    r"\baccording to\b",
    r"\bfrom the knowledge base\b",
]

AMBIGUOUS_QUERY_PATTERNS = [
    r"\bwhich one\b",
    r"\bwhich is better\b",
    r"\bwhat should i choose\b",
    r"\bcompare them\b",
    r"\bcompare those\b",
    r"\bis that better\b",
]


def _tokenize(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", value.lower()))


def load_knowledge_base() -> list[KnowledgeBaseEntry]:
    path = DATA_DIR / "knowledge_base.json"
    with path.open("r", encoding="utf-8") as handle:
        raw_entries = json.load(handle)

    return [
        KnowledgeBaseEntry(
            id=entry["id"],
            title=entry["title"],
            text=entry["text"],
            tags=list(entry.get("tags", [])),
        )
        for entry in raw_entries
    ]


class LocalKnowledgeBase:
    """Very small deterministic search layer used for local checks and Sprint 2 prep."""

    def __init__(self, entries: list[KnowledgeBaseEntry]) -> None:
        self.entries = entries

    def search(self, query: str, top_k: int = 3) -> list[dict[str, Any]]:
        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        scored: list[tuple[int, KnowledgeBaseEntry]] = []
        for entry in self.entries:
            haystack = " ".join([entry.title, entry.text, " ".join(entry.tags)])
            score = len(query_tokens & _tokenize(haystack))
            if score > 0:
                scored.append((score, entry))

        scored.sort(key=lambda item: (-item[0], item[1].id))
        return [
            {
                "id": entry.id,
                "title": entry.title,
                "score": score,
                "text": entry.text,
                "tags": entry.tags,
            }
            for score, entry in scored[:top_k]
        ]

    def decide_retrieval(self, query: str, top_k: int = 2) -> RetrievalDecision:
        normalized = " ".join(query.lower().split())
        warnings: list[str] = []
        looks_like_memory_query = any(re.search(pattern, normalized) for pattern in MEMORY_ONLY_PATTERNS)
        looks_like_knowledge_query = any(
            re.search(pattern, normalized) for pattern in KNOWLEDGE_QUERY_PATTERNS
        )
        looks_ambiguous = any(re.search(pattern, normalized) for pattern in AMBIGUOUS_QUERY_PATTERNS)

        query_type = "unknown"
        if looks_like_memory_query:
            query_type = "memory"
        elif looks_like_knowledge_query:
            query_type = "knowledge"

        if looks_ambiguous:
            warnings.append("query is underspecified and may need clarification")
            return RetrievalDecision(
                should_retrieve=False,
                reason="query is too ambiguous to ground safely",
                query_type=query_type,
                needs_clarification=True,
                warnings=warnings,
                snippets=[],
            )

        for pattern in MEMORY_ONLY_PATTERNS:
            if re.search(pattern, normalized):
                return RetrievalDecision(
                    should_retrieve=False,
                    reason="query looks like a conversational memory recall request",
                    query_type=query_type,
                    needs_clarification=False,
                    warnings=warnings,
                    snippets=[],
                )

        candidates = self.search(query, top_k=top_k)
        if not candidates:
            if looks_like_knowledge_query:
                warnings.append("external grounding is missing for a knowledge-seeking query")
            return RetrievalDecision(
                should_retrieve=False,
                reason="knowledge base returned no relevant snippets",
                query_type=query_type,
                needs_clarification=looks_like_knowledge_query,
                warnings=warnings,
                snippets=[],
            )

        top_score = int(candidates[0]["score"])

        if top_score < 2 and not looks_like_knowledge_query:
            warnings.append("retrieval candidates were too weak to trust")
            return RetrievalDecision(
                should_retrieve=False,
                reason="snippet overlap was too weak to justify retrieval",
                query_type=query_type,
                needs_clarification=False,
                warnings=warnings,
                snippets=[],
            )

        selected_candidates = [
            item for item in candidates if int(item["score"]) >= max(2, top_score - 1)
        ]
        if not selected_candidates:
            warnings.append("retrieval candidates were filtered out for weak relevance")
            return RetrievalDecision(
                should_retrieve=False,
                reason="candidate snippets were too weak after relevance filtering",
                query_type=query_type,
                needs_clarification=looks_like_knowledge_query,
                warnings=warnings,
                snippets=[],
            )

        snippets = [
            RetrievedSnippet(
                id=item["id"],
                title=item["title"],
                text=item["text"],
                tags=list(item["tags"]),
                score=int(item["score"]),
            )
            for item in selected_candidates
        ]
        return RetrievalDecision(
            should_retrieve=True,
            reason="query appears to require external knowledge and relevant snippets were found",
            query_type=query_type,
            needs_clarification=False,
            warnings=warnings,
            snippets=snippets,
        )


def build_retrieval_block(snippets: list[RetrievedSnippet]) -> str:
    if not snippets:
        return "No external snippets retrieved for this turn."

    sections = []
    for snippet in snippets:
        sections.append(
            "\n".join(
                [
                    f"- snippet_id: {snippet.id}",
                    f"  title: {snippet.title}",
                    f"  score: {snippet.score}",
                    f"  text: {snippet.text}",
                ]
            )
        )
    return "\n".join(sections)
