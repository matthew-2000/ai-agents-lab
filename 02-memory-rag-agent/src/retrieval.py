"""Local retrieval pipeline for 02 - Memory + RAG Agent."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from typing import Any

from config import DATA_DIR


@dataclass(frozen=True)
class KnowledgeBaseEntry:
    """One local source document that can be chunked and searched."""

    id: str
    title: str
    text: str
    tags: list[str]


@dataclass(frozen=True)
class KnowledgeChunk:
    """One retrievable chunk derived from a local source document."""

    chunk_id: str
    source_id: str
    title: str
    text: str
    tags: list[str]
    position: int


@dataclass(frozen=True)
class RetrievedSnippet:
    """One retrieved snippet passed to the model."""

    id: str
    source_id: str
    title: str
    text: str
    tags: list[str]
    score: float


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
    r"\bwhere do i live\b",
    r"\bwhere am i based\b",
    r"\bwhat is my location\b",
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


def _tokenize(value: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", value.lower())


def _token_set(value: str) -> set[str]:
    return set(_tokenize(value))


def _normalize_whitespace(value: str) -> str:
    return " ".join(value.split())


def _split_sentences(text: str) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", _normalize_whitespace(text))
    return [sentence.strip() for sentence in sentences if sentence.strip()]


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


def build_chunks(
    entries: list[KnowledgeBaseEntry],
    sentences_per_chunk: int = 2,
    sentence_overlap: int = 1,
) -> list[KnowledgeChunk]:
    """Split each document into overlapping sentence chunks."""

    chunks: list[KnowledgeChunk] = []
    step = max(1, sentences_per_chunk - sentence_overlap)

    for entry in entries:
        sentences = _split_sentences(entry.text)
        if not sentences:
            continue

        chunk_index = 0
        for start in range(0, len(sentences), step):
            window = sentences[start : start + sentences_per_chunk]
            if not window:
                continue

            chunk_index += 1
            chunk_text = " ".join(window)
            chunks.append(
                KnowledgeChunk(
                    chunk_id=f"{entry.id}#chunk-{chunk_index:02d}",
                    source_id=entry.id,
                    title=entry.title,
                    text=chunk_text,
                    tags=entry.tags,
                    position=chunk_index,
                )
            )

            if start + sentences_per_chunk >= len(sentences):
                break

    return chunks


class LocalKnowledgeBase:
    """Deterministic chunked retriever with simple hybrid lexical scoring."""

    def __init__(self, entries: list[KnowledgeBaseEntry]) -> None:
        self.entries = entries
        self.chunks = build_chunks(entries)
        self._idf = self._build_idf_index(self.chunks)

    def _build_idf_index(self, chunks: list[KnowledgeChunk]) -> dict[str, float]:
        document_frequency: dict[str, int] = {}

        for chunk in chunks:
            for token in _token_set(" ".join([chunk.title, chunk.text, " ".join(chunk.tags)])):
                document_frequency[token] = document_frequency.get(token, 0) + 1

        total_chunks = max(1, len(chunks))
        return {
            token: math.log(1 + (total_chunks / (1 + frequency))) + 1.0
            for token, frequency in document_frequency.items()
        }

    def _score_chunk(self, chunk: KnowledgeChunk, query: str) -> float:
        query_tokens = _token_set(query)
        if not query_tokens:
            return 0.0

        title_tokens = _token_set(chunk.title)
        body_tokens = _token_set(chunk.text)
        tag_tokens = _token_set(" ".join(chunk.tags))
        query_text = _normalize_whitespace(query.lower())
        chunk_text = _normalize_whitespace(chunk.text.lower())
        title_text = _normalize_whitespace(chunk.title.lower())

        lexical_score = 0.0
        for token in query_tokens:
            lexical_score += self._idf.get(token, 0.5) * (1.0 if token in body_tokens else 0.0)
            lexical_score += self._idf.get(token, 0.5) * (0.75 if token in title_tokens else 0.0)
            lexical_score += self._idf.get(token, 0.5) * (0.5 if token in tag_tokens else 0.0)

        phrase_bonus = 0.0
        if query_text in chunk_text or query_text in title_text:
            phrase_bonus += 4.0

        bigrams = {
            " ".join(pair) for pair in zip(_tokenize(query)[:-1], _tokenize(query)[1:])
        }
        for bigram in bigrams:
            if bigram and (bigram in chunk_text or bigram in title_text):
                phrase_bonus += 1.25

        title_bonus = 1.0 if len(query_tokens & title_tokens) >= 2 else 0.0
        tag_bonus = 0.75 if query_tokens & tag_tokens else 0.0

        return lexical_score + phrase_bonus + title_bonus + tag_bonus

    def search(self, query: str, top_k: int = 4) -> list[dict[str, Any]]:
        if not _tokenize(query):
            return []

        scored: list[tuple[float, KnowledgeChunk]] = []
        for chunk in self.chunks:
            score = self._score_chunk(chunk, query)
            if score > 0:
                scored.append((score, chunk))

        scored.sort(key=lambda item: (-item[0], item[1].source_id, item[1].position))

        selected: list[tuple[float, KnowledgeChunk]] = []
        per_source_counts: dict[str, int] = {}
        for score, chunk in scored:
            if len(selected) >= top_k:
                break
            source_count = per_source_counts.get(chunk.source_id, 0)
            if source_count >= 2:
                continue
            selected.append((score, chunk))
            per_source_counts[chunk.source_id] = source_count + 1

        return [
            {
                "id": chunk.chunk_id,
                "source_id": chunk.source_id,
                "title": chunk.title,
                "score": round(score, 4),
                "text": chunk.text,
                "tags": chunk.tags,
            }
            for score, chunk in selected
        ]

    def decide_retrieval(self, query: str, top_k: int = 3) -> RetrievalDecision:
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

        if looks_like_memory_query:
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

        top_score = float(candidates[0]["score"])
        if top_score < 2.5 and not looks_like_knowledge_query:
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
            item for item in candidates if float(item["score"]) >= max(2.5, top_score * 0.55)
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
                source_id=item["source_id"],
                title=item["title"],
                text=item["text"],
                tags=list(item["tags"]),
                score=float(item["score"]),
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
                    f"- chunk_id: {snippet.id}",
                    f"  source_id: {snippet.source_id}",
                    f"  title: {snippet.title}",
                    f"  score: {snippet.score:.2f}",
                    f"  text: {snippet.text}",
                ]
            )
        )
    return "\n".join(sections)
