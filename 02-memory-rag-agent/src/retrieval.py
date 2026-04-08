"""Retrieval pipeline for 02 - Memory + RAG Agent."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any

from documents import DocumentChunk, RetrievedSnippet, SourceDocument


@dataclass(frozen=True)
class QueryAnalysis:
    """Structured analysis of a user query before retrieval."""

    original_query: str
    normalized_query: str
    query_type: str
    retrieval_mode: str
    rewritten_queries: list[str]
    metadata_filters: dict[str, str]
    warnings: list[str]


@dataclass(frozen=True)
class RetrievalDecision:
    """Result of deciding whether retrieval should run for a user turn."""

    should_retrieve: bool
    reason: str
    query_type: str
    needs_clarification: bool
    warnings: list[str]
    snippets: list[RetrievedSnippet]
    analysis: QueryAnalysis


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

COMPARISON_PATTERNS = [
    r"\bdifference between\b",
    r"\bcompare\b",
    r"\bversus\b",
    r"\bvs\b",
]

NAVIGATIONAL_PATTERNS = [
    r"\baccording to\b",
    r"\bin the docs\b",
    r"\bfrom the knowledge base\b",
    r"\bin the pdf\b",
    r"\bin the html\b",
]

AMBIGUOUS_QUERY_PATTERNS = [
    r"\bwhich one\b",
    r"\bwhich is better\b",
    r"\bwhat should i choose\b",
    r"\bcompare them\b",
    r"\bcompare those\b",
    r"\bis that better\b",
]

SYNONYM_MAP = {
    "rag": ["retrieval augmented generation"],
    "retrieval augmented generation": ["rag"],
    "bm25": ["sparse retrieval"],
    "sparse retrieval": ["bm25", "lexical retrieval"],
    "dense retrieval": ["embedding retrieval", "semantic retrieval"],
    "memory": ["conversation memory", "short term memory"],
    "docs": ["documentation"],
    "kb": ["knowledge base"],
}

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "how",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "the",
    "to",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
}


def _tokenize(value: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", value.lower())


def _token_set(value: str) -> set[str]:
    return set(_tokenize(value))


def _normalize_whitespace(value: str) -> str:
    return " ".join(value.split())


def _split_sentences(text: str) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", _normalize_whitespace(text))
    return [sentence.strip() for sentence in sentences if sentence.strip()]


def _split_paragraphs(text: str) -> list[str]:
    paragraphs = re.split(r"\n\s*\n+", text)
    return [paragraph.strip() for paragraph in paragraphs if paragraph.strip()]


def _char_ngrams(value: str, size: int = 3) -> set[str]:
    normalized = re.sub(r"\s+", " ", value.lower()).strip()
    if len(normalized) < size:
        return {normalized} if normalized else set()
    return {normalized[index : index + size] for index in range(len(normalized) - size + 1)}


def _jaccard_similarity(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    union = left | right
    if not union:
        return 0.0
    return len(left & right) / len(union)


def _safe_float(value: str | None) -> float:
    if value is None:
        return 0.0
    try:
        return float(value)
    except ValueError:
        return 0.0


def _extract_metadata_filters(query: str) -> dict[str, str]:
    normalized = query.lower()
    filters: dict[str, str] = {}

    if "json" in normalized or "knowledge base" in normalized or "kb" in normalized:
        filters["source_type"] = "json_record"
    elif "pdf" in normalized:
        filters["file_extension"] = "pdf"
    elif "html" in normalized or "website" in normalized or "web page" in normalized:
        filters["file_extension"] = "html"
    elif "markdown" in normalized or "md" in normalized:
        filters["file_extension"] = "md"

    if "italian" in normalized:
        filters["language"] = "it"
    elif "english" in normalized:
        filters["language"] = "en"

    if any(term in normalized for term in ["latest", "recent", "current", "newest"]):
        filters["freshness"] = "prefer_recent"

    if "trusted" in normalized or "official" in normalized:
        filters["trust_tier"] = "high"

    return filters


def _expand_query(query: str) -> list[str]:
    normalized = _normalize_whitespace(query.lower())
    expansions = [normalized]

    for phrase, synonyms in SYNONYM_MAP.items():
        if phrase not in normalized:
            continue
        expanded = normalized
        for synonym in synonyms:
            expanded = f"{expanded} {synonym}"
        expansions.append(_normalize_whitespace(expanded))

    query_terms = [term for term in _tokenize(normalized) if term not in STOPWORDS]
    if query_terms:
        expansions.append(" ".join(query_terms))

    unique_expansions: list[str] = []
    for expansion in expansions:
        if expansion and expansion not in unique_expansions:
            unique_expansions.append(expansion)
    return unique_expansions[:3]


def analyze_query(query: str) -> QueryAnalysis:
    """Classify the query and derive retrieval guidance."""

    normalized = _normalize_whitespace(query.lower())
    warnings: list[str] = []
    filters = _extract_metadata_filters(normalized)

    looks_like_memory_query = any(re.search(pattern, normalized) for pattern in MEMORY_ONLY_PATTERNS)
    looks_like_knowledge_query = any(re.search(pattern, normalized) for pattern in KNOWLEDGE_QUERY_PATTERNS)
    looks_like_comparison = any(re.search(pattern, normalized) for pattern in COMPARISON_PATTERNS)
    looks_like_navigational = any(re.search(pattern, normalized) for pattern in NAVIGATIONAL_PATTERNS)
    looks_ambiguous = any(re.search(pattern, normalized) for pattern in AMBIGUOUS_QUERY_PATTERNS)

    query_type = "unknown"
    if looks_like_memory_query:
        query_type = "memory"
    elif looks_like_comparison:
        query_type = "comparison"
    elif looks_like_navigational:
        query_type = "navigational"
    elif looks_like_knowledge_query:
        query_type = "knowledge"

    retrieval_mode = "none"
    if query_type in {"knowledge", "comparison", "navigational"}:
        retrieval_mode = "hybrid"

    if looks_ambiguous:
        warnings.append("query is underspecified and may need clarification")
    if filters.get("freshness") == "prefer_recent":
        warnings.append("freshness-sensitive query detected but local corpus has limited recency metadata")

    return QueryAnalysis(
        original_query=query,
        normalized_query=normalized,
        query_type=query_type,
        retrieval_mode=retrieval_mode,
        rewritten_queries=_expand_query(normalized),
        metadata_filters=filters,
        warnings=warnings,
    )


def build_chunks(
    documents: list[SourceDocument],
    max_sentences_per_chunk: int = 3,
    sentence_overlap: int = 1,
) -> list[DocumentChunk]:
    """Split documents into overlapping chunks while preserving metadata."""

    chunks: list[DocumentChunk] = []
    step = max(1, max_sentences_per_chunk - sentence_overlap)

    for document in documents:
        paragraphs = _split_paragraphs(document.text) or [document.text]
        chunk_index = 0

        for paragraph in paragraphs:
            sentences = _split_sentences(paragraph)
            if not sentences:
                sentences = [paragraph.strip()]

            for start in range(0, len(sentences), step):
                window = sentences[start : start + max_sentences_per_chunk]
                if not window:
                    continue

                chunk_index += 1
                chunks.append(
                    DocumentChunk(
                        chunk_id=f"{document.doc_id}#chunk-{chunk_index:02d}",
                        doc_id=document.doc_id,
                        source_type=document.source_type,
                        title=document.title,
                        text=" ".join(window),
                        tags=list(document.tags),
                        position=chunk_index,
                        section=document.section,
                        url=document.url,
                        updated_at=document.updated_at,
                        language=document.language,
                        trust_score=document.trust_score,
                        metadata=dict(document.metadata),
                    )
                )

                if start + max_sentences_per_chunk >= len(sentences):
                    break

    return chunks


class LocalKnowledgeBase:
    """Deterministic hybrid retriever with local reranking and metadata filters."""

    def __init__(self, documents: list[SourceDocument]) -> None:
        self.documents = documents
        self.chunks = build_chunks(documents)
        self._idf = self._build_idf_index(self.chunks)

    def _build_idf_index(self, chunks: list[DocumentChunk]) -> dict[str, float]:
        document_frequency: dict[str, int] = {}

        for chunk in chunks:
            combined = " ".join(
                [
                    chunk.title,
                    chunk.text,
                    " ".join(chunk.tags),
                    chunk.section or "",
                    chunk.source_type,
                ]
            )
            for token in _token_set(combined):
                document_frequency[token] = document_frequency.get(token, 0) + 1

        total_chunks = max(1, len(chunks))
        return {
            token: math.log(1 + (total_chunks / (1 + frequency))) + 1.0
            for token, frequency in document_frequency.items()
        }

    def _chunk_matches_filters(self, chunk: DocumentChunk, filters: dict[str, str]) -> bool:
        if not filters:
            return True

        file_name = str(chunk.metadata.get("file_name") or "").lower()
        if filters.get("source_type") and chunk.source_type != filters["source_type"]:
            return False
        if filters.get("file_extension") and not file_name.endswith(f".{filters['file_extension']}"):
            return False
        if filters.get("language") and not chunk.language.lower().startswith(filters["language"]):
            return False
        if filters.get("trust_tier") == "high" and chunk.trust_score < 0.8:
            return False
        return True

    def _lexical_score(self, chunk: DocumentChunk, query: str) -> float:
        query_tokens = _token_set(query)
        if not query_tokens:
            return 0.0

        title_tokens = _token_set(chunk.title)
        body_tokens = _token_set(chunk.text)
        tag_tokens = _token_set(" ".join(chunk.tags))
        section_tokens = _token_set(chunk.section or "")
        query_text = _normalize_whitespace(query.lower())
        chunk_text = _normalize_whitespace(chunk.text.lower())
        title_text = _normalize_whitespace(chunk.title.lower())

        lexical_score = 0.0
        for token in query_tokens:
            lexical_score += self._idf.get(token, 0.5) * (1.0 if token in body_tokens else 0.0)
            lexical_score += self._idf.get(token, 0.5) * (0.85 if token in title_tokens else 0.0)
            lexical_score += self._idf.get(token, 0.5) * (0.55 if token in tag_tokens else 0.0)
            lexical_score += self._idf.get(token, 0.5) * (0.35 if token in section_tokens else 0.0)

        phrase_bonus = 0.0
        if query_text in chunk_text or query_text in title_text:
            phrase_bonus += 4.0

        query_terms = _tokenize(query)
        bigrams = {" ".join(pair) for pair in zip(query_terms[:-1], query_terms[1:])}
        for bigram in bigrams:
            if bigram and (bigram in chunk_text or bigram in title_text):
                phrase_bonus += 1.25

        title_bonus = 1.0 if len(query_tokens & title_tokens) >= 2 else 0.0
        tag_bonus = 0.75 if query_tokens & tag_tokens else 0.0
        trust_bonus = min(1.0, max(0.0, chunk.trust_score)) * 0.35

        return lexical_score + phrase_bonus + title_bonus + tag_bonus + trust_bonus

    def _semantic_score(self, chunk: DocumentChunk, query: str) -> float:
        query_terms = set(_tokenize(query)) - STOPWORDS
        combined_text = " ".join(
            [chunk.title, chunk.text, " ".join(chunk.tags), chunk.section or ""]
        )
        chunk_terms = set(_tokenize(combined_text)) - STOPWORDS
        token_similarity = _jaccard_similarity(query_terms, chunk_terms)

        query_ngrams = _char_ngrams(query)
        chunk_ngrams = _char_ngrams(combined_text)
        ngram_similarity = _jaccard_similarity(query_ngrams, chunk_ngrams)

        title_similarity = _jaccard_similarity(_char_ngrams(query), _char_ngrams(chunk.title))
        return (token_similarity * 5.0) + (ngram_similarity * 3.0) + (title_similarity * 2.0)

    def _rerank_score(self, chunk: DocumentChunk, query: str, filters: dict[str, str]) -> float:
        query_terms = set(_tokenize(query)) - STOPWORDS
        chunk_terms = set(_tokenize(" ".join([chunk.title, chunk.text]))) - STOPWORDS
        coverage = len(query_terms & chunk_terms) / max(1, len(query_terms))

        title_terms = _token_set(chunk.title)
        title_coverage = len(query_terms & title_terms) / max(1, len(query_terms))
        filter_bonus = 0.4 if self._chunk_matches_filters(chunk, filters) and filters else 0.0
        recency_bonus = 0.0
        if filters.get("freshness") == "prefer_recent":
            recency_bonus = min(0.35, _safe_float(chunk.updated_at[-4:]) * 0.0) if chunk.updated_at else 0.0
        return (coverage * 2.8) + (title_coverage * 1.6) + filter_bonus + recency_bonus

    def search(self, query: str, top_k: int = 4) -> list[dict[str, Any]]:
        analysis = analyze_query(query)
        if not _tokenize(query):
            return []

        scored: list[tuple[float, float, float, float, DocumentChunk]] = []
        for chunk in self.chunks:
            if not self._chunk_matches_filters(chunk, analysis.metadata_filters):
                continue

            lexical = 0.0
            semantic = 0.0
            for rewritten_query in analysis.rewritten_queries:
                lexical = max(lexical, self._lexical_score(chunk, rewritten_query))
                semantic = max(semantic, self._semantic_score(chunk, rewritten_query))

            if lexical <= 0 and semantic <= 0:
                continue

            hybrid = (lexical * 0.72) + (semantic * 1.45)
            rerank = self._rerank_score(chunk, analysis.rewritten_queries[0], analysis.metadata_filters)
            total = hybrid + rerank
            scored.append((total, lexical, semantic, rerank, chunk))

        scored.sort(key=lambda item: (-item[0], -item[1], item[4].doc_id, item[4].position))

        selected: list[tuple[float, float, float, float, DocumentChunk]] = []
        seen_texts: set[str] = set()
        per_doc_counts: dict[str, int] = {}
        for total, lexical, semantic, rerank, chunk in scored:
            if len(selected) >= top_k:
                break

            doc_count = per_doc_counts.get(chunk.doc_id, 0)
            if doc_count >= 2:
                continue

            normalized_text = _normalize_whitespace(chunk.text.lower())
            if normalized_text in seen_texts:
                continue

            selected.append((total, lexical, semantic, rerank, chunk))
            seen_texts.add(normalized_text)
            per_doc_counts[chunk.doc_id] = doc_count + 1

        return [
            {
                "id": chunk.chunk_id,
                "doc_id": chunk.doc_id,
                "source_type": chunk.source_type,
                "title": chunk.title,
                "score": round(total, 4),
                "text": chunk.text,
                "tags": chunk.tags,
                "section": chunk.section,
                "url": chunk.url,
                "updated_at": chunk.updated_at,
                "language": chunk.language,
                "trust_score": round(chunk.trust_score, 4),
                "metadata": {
                    **dict(chunk.metadata),
                    "scores": {
                        "lexical": round(lexical, 4),
                        "semantic": round(semantic, 4),
                        "rerank": round(rerank, 4),
                    },
                    "query_analysis": {
                        "query_type": analysis.query_type,
                        "retrieval_mode": analysis.retrieval_mode,
                        "filters": analysis.metadata_filters,
                    },
                },
            }
            for total, lexical, semantic, rerank, chunk in selected
        ]

    def decide_retrieval(self, query: str, top_k: int = 3) -> RetrievalDecision:
        analysis = analyze_query(query)
        warnings = list(analysis.warnings)

        if "query is underspecified and may need clarification" in warnings:
            return RetrievalDecision(
                should_retrieve=False,
                reason="query is too ambiguous to ground safely",
                query_type=analysis.query_type,
                needs_clarification=True,
                warnings=warnings,
                snippets=[],
                analysis=analysis,
            )

        if analysis.query_type == "memory":
            return RetrievalDecision(
                should_retrieve=False,
                reason="query looks like a conversational memory recall request",
                query_type=analysis.query_type,
                needs_clarification=False,
                warnings=warnings,
                snippets=[],
                analysis=analysis,
            )

        candidates = self.search(query, top_k=max(top_k + 2, 5))
        if not candidates:
            if analysis.query_type in {"knowledge", "comparison", "navigational"}:
                warnings.append("external grounding is missing for a knowledge-seeking query")
            return RetrievalDecision(
                should_retrieve=False,
                reason="knowledge base returned no relevant snippets",
                query_type=analysis.query_type,
                needs_clarification=analysis.query_type in {"knowledge", "comparison", "navigational"},
                warnings=warnings,
                snippets=[],
                analysis=analysis,
            )

        top_score = float(candidates[0]["score"])
        score_floor = 3.0 if analysis.query_type in {"knowledge", "comparison", "navigational"} else 4.0
        if top_score < score_floor and analysis.query_type not in {"knowledge", "comparison", "navigational"}:
            warnings.append("retrieval candidates were too weak to trust")
            return RetrievalDecision(
                should_retrieve=False,
                reason="snippet overlap was too weak to justify retrieval",
                query_type=analysis.query_type,
                needs_clarification=False,
                warnings=warnings,
                snippets=[],
                analysis=analysis,
            )

        selected_candidates = [
            item for item in candidates if float(item["score"]) >= max(score_floor, top_score * 0.58)
        ][:top_k]
        if not selected_candidates:
            warnings.append("retrieval candidates were filtered out for weak relevance")
            return RetrievalDecision(
                should_retrieve=False,
                reason="candidate snippets were too weak after relevance filtering",
                query_type=analysis.query_type,
                needs_clarification=analysis.query_type in {"knowledge", "comparison", "navigational"},
                warnings=warnings,
                snippets=[],
                analysis=analysis,
            )

        snippets = [
            RetrievedSnippet(
                id=str(item["id"]),
                doc_id=str(item["doc_id"]),
                source_type=str(item["source_type"]),
                title=str(item["title"]),
                text=str(item["text"]),
                tags=list(item["tags"]),
                score=float(item["score"]),
                section=item.get("section"),
                url=item.get("url"),
                updated_at=item.get("updated_at"),
                language=str(item.get("language") or "en"),
                trust_score=float(item.get("trust_score") or 0.75),
                metadata=dict(item.get("metadata") or {}),
            )
            for item in selected_candidates
        ]
        return RetrievalDecision(
            should_retrieve=True,
            reason="hybrid retrieval found relevant snippets after query analysis and reranking",
            query_type=analysis.query_type,
            needs_clarification=False,
            warnings=warnings,
            snippets=snippets,
            analysis=analysis,
        )


def build_retrieval_block(snippets: list[RetrievedSnippet]) -> str:
    if not snippets:
        return "No external snippets retrieved for this turn."

    sections = []
    for snippet in snippets:
        section_label = snippet.section or "n/a"
        url_label = snippet.url or "n/a"
        score_details = snippet.metadata.get("scores", {})
        lexical = score_details.get("lexical", "n/a")
        semantic = score_details.get("semantic", "n/a")
        rerank = score_details.get("rerank", "n/a")
        sections.append(
            "\n".join(
                [
                    f"- chunk_id: {snippet.id}",
                    f"  doc_id: {snippet.doc_id}",
                    f"  source_type: {snippet.source_type}",
                    f"  title: {snippet.title}",
                    f"  section: {section_label}",
                    f"  url: {url_label}",
                    f"  trust_score: {snippet.trust_score:.2f}",
                    f"  total_score: {snippet.score:.2f}",
                    f"  lexical_score: {lexical}",
                    f"  semantic_score: {semantic}",
                    f"  rerank_score: {rerank}",
                    f"  text: {snippet.text}",
                ]
            )
        )
    return "\n".join(sections)
