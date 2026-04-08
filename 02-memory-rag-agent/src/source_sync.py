"""Trusted online source sync for 02 - Memory + RAG Agent."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from config import REMOTE_CACHE_DIR, SOURCES_DIR
from documents import SourceDocument


DEFAULT_SOURCE_CATALOG_PATH = SOURCES_DIR / "trusted_sources.json"
DEFAULT_GOVERNANCE_PATH = SOURCES_DIR / "source_governance.json"
DEFAULT_SYNC_MANIFEST_PATH = REMOTE_CACHE_DIR / "manifest.json"


@dataclass(frozen=True)
class GovernanceRule:
    """Governance rule for one trusted host."""

    host: str
    trust_score: float
    source_type: str
    allow_subdomains: bool
    allowed_prefixes: list[str]
    freshness_sensitive: bool


@dataclass(frozen=True)
class RemoteSourceSpec:
    """One online source to sync into the local corpus."""

    id: str
    title: str
    url: str
    canonical_url: str | None = None
    source_type: str | None = None
    language: str = "en"
    tags: list[str] | None = None
    trust_score: float | None = None
    section: str | None = None
    updated_at: str | None = None
    allow_file_url: bool = False
    notes: str | None = None


@dataclass(frozen=True)
class SyncRecord:
    """One sync outcome row."""

    source_id: str
    status: str
    url: str
    cache_path: str | None
    content_hash: str | None
    message: str


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_governance_rules(path: Path = DEFAULT_GOVERNANCE_PATH) -> dict[str, GovernanceRule]:
    payload = _read_json(path)
    rules: dict[str, GovernanceRule] = {}
    for entry in payload:
        rules[str(entry["host"])] = GovernanceRule(
            host=str(entry["host"]),
            trust_score=float(entry.get("trust_score", 0.85)),
            source_type=str(entry.get("source_type", "remote_web")),
            allow_subdomains=bool(entry.get("allow_subdomains", False)),
            allowed_prefixes=[str(value) for value in entry.get("allowed_prefixes", ["/"])],
            freshness_sensitive=bool(entry.get("freshness_sensitive", False)),
        )
    return rules


def load_source_catalog(path: Path = DEFAULT_SOURCE_CATALOG_PATH) -> list[RemoteSourceSpec]:
    payload = _read_json(path)
    catalog: list[RemoteSourceSpec] = []
    for entry in payload:
        catalog.append(
            RemoteSourceSpec(
                id=str(entry["id"]),
                title=str(entry["title"]),
                url=str(entry["url"]),
                canonical_url=entry.get("canonical_url"),
                source_type=entry.get("source_type"),
                language=str(entry.get("language", "en")),
                tags=[str(tag) for tag in entry.get("tags", [])],
                trust_score=float(entry["trust_score"]) if entry.get("trust_score") is not None else None,
                section=entry.get("section"),
                updated_at=entry.get("updated_at"),
                allow_file_url=bool(entry.get("allow_file_url", False)),
                notes=entry.get("notes"),
            )
        )
    return catalog


def _load_manifest(path: Path = DEFAULT_SYNC_MANIFEST_PATH) -> dict[str, Any]:
    if not path.exists():
        return {"sources": {}}
    return _read_json(path)


def _write_manifest(payload: dict[str, Any], path: Path = DEFAULT_SYNC_MANIFEST_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=True)


def _slugify(value: str) -> str:
    collapsed = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return collapsed or "source"


def _normalize_whitespace(value: str) -> str:
    return " ".join(value.split())


def _extract_title_from_html(raw_html: str) -> str | None:
    match = re.search(r"<title>(.*?)</title>", raw_html, flags=re.IGNORECASE | re.DOTALL)
    if match:
        return _normalize_whitespace(re.sub(r"<[^>]+>", " ", match.group(1)))

    h1_match = re.search(r"<h1[^>]*>(.*?)</h1>", raw_html, flags=re.IGNORECASE | re.DOTALL)
    if h1_match:
        return _normalize_whitespace(re.sub(r"<[^>]+>", " ", h1_match.group(1)))
    return None


def _html_to_text(raw_html: str) -> str:
    without_scripts = re.sub(
        r"<script.*?>.*?</script>",
        " ",
        raw_html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    without_styles = re.sub(
        r"<style.*?>.*?</style>",
        " ",
        without_scripts,
        flags=re.IGNORECASE | re.DOTALL,
    )
    without_tags = re.sub(r"<[^>]+>", " ", without_styles)
    return _normalize_whitespace(without_tags)


def _compute_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _match_governance_rule(canonical_url: str, rules: dict[str, GovernanceRule]) -> GovernanceRule:
    parsed = urlparse(canonical_url)
    host = (parsed.hostname or "").lower()
    path = parsed.path or "/"

    for candidate_host, rule in rules.items():
        exact_match = host == candidate_host
        subdomain_match = rule.allow_subdomains and host.endswith(f".{candidate_host}")
        if not (exact_match or subdomain_match):
            continue
        if not any(path.startswith(prefix) for prefix in rule.allowed_prefixes):
            continue
        return rule

    raise RuntimeError(f"URL '{canonical_url}' is not allowed by source governance.")


def _fetch_remote_content(spec: RemoteSourceSpec) -> tuple[str, dict[str, str]]:
    parsed = urlparse(spec.url)
    if parsed.scheme == "file":
        if not spec.allow_file_url:
            raise RuntimeError(f"File URL is not allowed for source '{spec.id}'.")
        path = Path(parsed.path)
        raw_text = path.read_text(encoding="utf-8")
        return raw_text, {"content-type": "text/html", "source": "file"}

    request = Request(
        spec.url,
        headers={
            "User-Agent": "ai-agents-lab-rag-sync/1.0 (+https://example.local)",
            "Accept": "text/html,application/xhtml+xml,text/plain",
        },
    )
    with urlopen(request, timeout=15) as response:  # noqa: S310
        payload = response.read()
        headers = {key.lower(): value for key, value in response.headers.items()}
    content_type = headers.get("content-type", "")
    if "charset=" in content_type:
        charset = content_type.split("charset=")[-1].split(";")[0].strip()
    else:
        charset = "utf-8"
    return payload.decode(charset, errors="replace"), headers


def _build_remote_document(
    spec: RemoteSourceSpec,
    governance: GovernanceRule,
    raw_content: str,
    headers: dict[str, str],
) -> SourceDocument:
    canonical_url = spec.canonical_url or spec.url
    title = spec.title
    content_type = headers.get("content-type", "text/html")
    if "html" in content_type or canonical_url.endswith((".html", ".htm")) or "<html" in raw_content.lower():
        extracted_title = _extract_title_from_html(raw_content)
        if extracted_title:
            title = extracted_title
        text = _html_to_text(raw_content)
    else:
        text = _normalize_whitespace(raw_content)

    if not text:
        raise RuntimeError(f"Fetched source '{spec.id}' did not produce any retrievable text.")

    updated_at = spec.updated_at or headers.get("last-modified")
    sync_time = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return SourceDocument(
        doc_id=spec.id,
        source_type=spec.source_type or governance.source_type,
        title=title,
        text=text,
        url=canonical_url,
        section=spec.section or governance.host,
        updated_at=updated_at,
        language=spec.language,
        tags=list(spec.tags or []),
        trust_score=float(spec.trust_score if spec.trust_score is not None else governance.trust_score),
        metadata={
            "host": governance.host,
            "freshness_sensitive": governance.freshness_sensitive,
            "notes": spec.notes or "",
            "synced_at": sync_time,
            "content_type": headers.get("content-type", ""),
        },
    )


def sync_online_sources(
    catalog_path: Path = DEFAULT_SOURCE_CATALOG_PATH,
    governance_path: Path = DEFAULT_GOVERNANCE_PATH,
    cache_dir: Path = REMOTE_CACHE_DIR,
    manifest_path: Path = DEFAULT_SYNC_MANIFEST_PATH,
    force: bool = False,
) -> list[SyncRecord]:
    """Fetch trusted online sources into the local cache with incremental sync."""

    cache_dir.mkdir(parents=True, exist_ok=True)
    governance_rules = load_governance_rules(governance_path)
    catalog = load_source_catalog(catalog_path)
    manifest = _load_manifest(manifest_path)
    results: list[SyncRecord] = []

    for spec in catalog:
        canonical_url = spec.canonical_url or spec.url
        rule = _match_governance_rule(canonical_url, governance_rules)
        raw_content, headers = _fetch_remote_content(spec)
        document = _build_remote_document(spec, rule, raw_content, headers)
        content_hash = _compute_hash(document.text)
        previous = manifest.setdefault("sources", {}).get(spec.id)

        cache_path = cache_dir / f"{_slugify(spec.id)}.json"
        if not force and previous and previous.get("content_hash") == content_hash and cache_path.exists():
            results.append(
                SyncRecord(
                    source_id=spec.id,
                    status="unchanged",
                    url=canonical_url,
                    cache_path=str(cache_path),
                    content_hash=content_hash,
                    message="source content unchanged; reused cached snapshot",
                )
            )
            continue

        with cache_path.open("w", encoding="utf-8") as handle:
            json.dump(asdict(document), handle, indent=2, ensure_ascii=True)

        manifest["sources"][spec.id] = {
            "content_hash": content_hash,
            "cache_path": str(cache_path),
            "canonical_url": canonical_url,
            "synced_at": document.metadata.get("synced_at"),
        }
        results.append(
            SyncRecord(
                source_id=spec.id,
                status="updated" if previous else "created",
                url=canonical_url,
                cache_path=str(cache_path),
                content_hash=content_hash,
                message="source fetched and cached successfully",
            )
        )

    _write_manifest(manifest, manifest_path)
    return results


def load_cached_remote_documents(cache_dir: Path = REMOTE_CACHE_DIR) -> list[SourceDocument]:
    """Load cached remote documents that were previously synced."""

    if not cache_dir.exists():
        return []

    documents: list[SourceDocument] = []
    for path in sorted(cache_dir.glob("*.json")):
        if path.name == "manifest.json":
            continue
        payload = _read_json(path)
        documents.append(
            SourceDocument(
                doc_id=str(payload["doc_id"]),
                source_type=str(payload["source_type"]),
                title=str(payload["title"]),
                text=str(payload["text"]),
                url=payload.get("url"),
                section=payload.get("section"),
                updated_at=payload.get("updated_at"),
                language=str(payload.get("language", "en")),
                tags=[str(tag) for tag in payload.get("tags", [])],
                trust_score=float(payload.get("trust_score", 0.8)),
                metadata=dict(payload.get("metadata", {})),
            )
        )
    return documents
