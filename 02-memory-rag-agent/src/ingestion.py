"""Local ingestion pipeline for 02 - Memory + RAG Agent."""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Iterable

from config import DATA_DIR
from documents import SourceDocument
from source_sync import load_cached_remote_documents


SUPPORTED_TEXT_EXTENSIONS = {".json", ".md", ".txt", ".html", ".htm"}
SUPPORTED_BINARY_EXTENSIONS = {".pdf"}


def _slugify(value: str) -> str:
    collapsed = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return collapsed or "document"


def _normalize_whitespace(value: str) -> str:
    return " ".join(value.split())


def _infer_title_from_text(path: Path, text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip().lstrip("#").strip()
        if stripped:
            return stripped[:120]
    return path.stem.replace("_", " ").replace("-", " ").title()


def _read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _read_html_file(path: Path) -> str:
    raw_text = path.read_text(encoding="utf-8")
    without_tags = re.sub(r"<script.*?>.*?</script>", " ", raw_text, flags=re.IGNORECASE | re.DOTALL)
    without_tags = re.sub(r"<style.*?>.*?</style>", " ", without_tags, flags=re.IGNORECASE | re.DOTALL)
    without_tags = re.sub(r"<[^>]+>", " ", without_tags)
    return _normalize_whitespace(without_tags)


def _read_pdf_file(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        return ""

    reader = PdfReader(str(path))
    pages: list[str] = []
    for page in reader.pages:
        page_text = page.extract_text() or ""
        if page_text.strip():
            pages.append(page_text)
    return _normalize_whitespace("\n".join(pages))


def _load_json_records(path: Path) -> list[SourceDocument]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if not isinstance(payload, list):
        return []

    documents: list[SourceDocument] = []
    for index, entry in enumerate(payload, start=1):
        if not isinstance(entry, dict):
            continue

        text = _normalize_whitespace(str(entry.get("text", "")))
        if not text:
            continue

        doc_id = str(entry.get("doc_id") or entry.get("id") or f"{path.stem}-{index:03d}")
        metadata = {
            "file_name": path.name,
            "record_index": str(index),
        }
        if entry.get("author"):
            metadata["author"] = str(entry["author"])

        documents.append(
            SourceDocument(
                doc_id=doc_id,
                source_type=str(entry.get("source_type") or "json_record"),
                title=str(entry.get("title") or f"{path.stem} record {index}"),
                text=text,
                url=entry.get("url"),
                section=entry.get("section"),
                updated_at=entry.get("updated_at"),
                language=str(entry.get("language") or "en"),
                tags=[str(tag) for tag in entry.get("tags", [])],
                trust_score=float(entry.get("trust_score", 0.8)),
                metadata=metadata,
            )
        )

    return documents


def _load_text_document(path: Path) -> SourceDocument | None:
    suffix = path.suffix.lower()
    if suffix in {".md", ".txt"}:
        text = _normalize_whitespace(_read_text_file(path))
    elif suffix in {".html", ".htm"}:
        text = _read_html_file(path)
    elif suffix == ".pdf":
        text = _read_pdf_file(path)
    else:
        return None

    if not text:
        return None

    title = _infer_title_from_text(path, text)
    return SourceDocument(
        doc_id=f"file-{_slugify(path.stem)}",
        source_type="local_file",
        title=title,
        text=text,
        section=path.name,
        language="en",
        tags=[path.suffix.lower().lstrip(".") or "text"],
        trust_score=0.72,
        metadata={"file_name": path.name},
    )


def _iter_candidate_files(data_dir: Path) -> Iterable[Path]:
    for path in sorted(data_dir.iterdir()):
        if not path.is_file():
            continue
        if path.name.startswith("."):
            continue
        if path.suffix.lower() in SUPPORTED_TEXT_EXTENSIONS | SUPPORTED_BINARY_EXTENSIONS:
            yield path


def load_source_documents(data_dir: Path = DATA_DIR) -> list[SourceDocument]:
    """Load normalized source documents from the local data directory."""

    documents: list[SourceDocument] = []
    for path in _iter_candidate_files(data_dir):
        suffix = path.suffix.lower()
        if suffix == ".json":
            documents.extend(_load_json_records(path))
            continue

        document = _load_text_document(path)
        if document is not None:
            documents.append(document)

    documents.extend(load_cached_remote_documents())
    return documents
