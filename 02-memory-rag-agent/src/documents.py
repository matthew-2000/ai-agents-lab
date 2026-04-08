"""Canonical document and retrieval models for 02 - Memory + RAG Agent."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SourceDocument:
    """Normalized source document ready for chunking and indexing."""

    doc_id: str
    source_type: str
    title: str
    text: str
    url: str | None = None
    section: str | None = None
    updated_at: str | None = None
    language: str = "en"
    tags: list[str] = field(default_factory=list)
    trust_score: float = 0.75
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DocumentChunk:
    """One retrievable chunk derived from a normalized source document."""

    chunk_id: str
    doc_id: str
    source_type: str
    title: str
    text: str
    tags: list[str]
    position: int
    section: str | None = None
    url: str | None = None
    updated_at: str | None = None
    language: str = "en"
    trust_score: float = 0.75
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RetrievedSnippet:
    """One retrieved snippet passed to the model and surfaced to the user."""

    id: str
    doc_id: str
    source_type: str
    title: str
    text: str
    tags: list[str]
    score: float
    section: str | None = None
    url: str | None = None
    updated_at: str | None = None
    language: str = "en"
    trust_score: float = 0.75
    metadata: dict[str, Any] = field(default_factory=dict)
