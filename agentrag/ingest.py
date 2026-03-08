from __future__ import annotations

import hashlib
import json
import logging
import re
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from agentrag.chunkers.code import chunk_code
from agentrag.chunkers.text import chunk_text
from agentrag.models import CodeMetadata, GlobalMetadata, Payload, TextMetadata, VectorNode
from agentrag.providers.embeddings import EmbeddingProvider
from agentrag.qdrant_store import QdrantStore

TEXT_EXTS = {".md", ".txt", ".rst"}
WEB_DOC_EXTS = {".md", ".txt", ".rst", ".pdf", ".docx", ".doc", ".html", ".htm"}
CODE_EXTS = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".java": "java",
    ".go": "go",
    ".cpp": "cpp",
    ".c": "c",
    ".rs": "rust",
}

logger = logging.getLogger(__name__)

_EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001F5FF"
    "\U0001F600-\U0001F64F"
    "\U0001F680-\U0001F6FF"
    "\U0001F700-\U0001F77F"
    "\U0001F780-\U0001F7FF"
    "\U0001F800-\U0001F8FF"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FAFF"
    "\U00002700-\U000027BF"
    "\U00002600-\U000026FF"
    "]+"
)
_MENU_LINE_RE = re.compile(
    r"(?i)\b(home|menu|navigation|login|sign\s*in|sign\s*up|register|contact|privacy|terms|cookie|share|subscribe|search)\b"
)
_SEPARATOR_RE = re.compile(r"^[\s\-_=*~`|•·:]+$")


@dataclass
class IngestResult:
    nodes_created: int
    skipped: int
    new_chunks: int
    unchanged_chunks: int
    stale_deleted: int


def _read_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _is_http_url(value: str) -> bool:
    parsed = urlparse(value.strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _infer_web_document_type(url: str) -> str:
    ext = Path(urlparse(url).path).suffix.lower()
    if ext in WEB_DOC_EXTS:
        return ext.lstrip(".")
    return "web"


def _fetch_web_content_via_jina(
    url: str,
    jina_reader_base_url: str = "https://r.jina.ai/",
    request_timeout_seconds: float = 45.0,
) -> str:
    reader = jina_reader_base_url.rstrip("/") + "/" + url
    req = Request(
        reader,
        headers={
            "User-Agent": "agentRAG/0.1 (+https://r.jina.ai)",
            "Accept": "text/plain, text/markdown; q=0.9, */*; q=0.8",
        },
    )
    with urlopen(req, timeout=request_timeout_seconds) as resp:
        raw = resp.read()
    return raw.decode("utf-8", errors="ignore")


def sanitize_web_content(content: str) -> str:
    text = content.replace("\r\n", "\n").replace("\r", "\n")
    lines = [ln.strip() for ln in text.split("\n")]
    cleaned: list[str] = []
    seen = set()
    for ln in lines:
        if not ln:
            if cleaned and cleaned[-1] != "":
                cleaned.append("")
            continue
        ln = _EMOJI_RE.sub(" ", ln)
        ln = re.sub(r"\s+", " ", ln).strip()
        if not ln:
            continue
        if _SEPARATOR_RE.fullmatch(ln):
            continue
        if _MENU_LINE_RE.search(ln) and len(ln) <= 80:
            continue
        if ln.lower().startswith(("copyright ", "all rights reserved")):
            continue
        # Remove exact repeated boilerplate lines (header/footer duplication).
        key = ln.lower()
        if key in seen and len(ln) <= 120:
            continue
        seen.add(key)
        cleaned.append(ln)

    out = "\n".join(cleaned)
    out = re.sub(r"\n{3,}", "\n\n", out).strip()
    return out


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _point_id_from_source_hash(source_id: str, content_hash: str) -> str:
    # Stable chunk identity for re-ingest: hash(source_id + content_hash)
    stable = _sha(f"{source_id}:{content_hash}")
    return str(uuid.UUID(hex=stable[:32]))


def ingest_paths(
    paths: list[Path],
    store: QdrantStore,
    embedder: EmbeddingProvider,
    access_level: str = "internal",
    dry_run: bool = False,
) -> IngestResult:
    nodes_created = 0
    skipped = 0
    new_chunks = 0
    unchanged_chunks = 0
    stale_deleted = 0

    valid_paths: list[Path] = []
    for path in paths:
        if not path.exists() or not path.is_file():
            skipped += 1
            continue
        ext = path.suffix.lower()
        if ext not in TEXT_EXTS and ext not in CODE_EXTS:
            skipped += 1
            continue
        valid_paths.append(path)

    if not valid_paths:
        return IngestResult(
            nodes_created=nodes_created,
            skipped=skipped,
            new_chunks=new_chunks,
            unchanged_chunks=unchanged_chunks,
            stale_deleted=stale_deleted,
        )

    store.ensure_collection()

    for path in valid_paths:
        started_at = time.perf_counter()
        source_id = str(path.resolve())
        content = _read_file(path)
        if not content.strip():
            skipped += 1
            continue

        ext = path.suffix.lower()
        last_modified = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        existing_ids = store.list_point_ids_by_source_id(source_id)

        nodes_to_upsert: list[VectorNode] = []
        current_ids: set[str] = set()

        if ext in TEXT_EXTS:
            for idx, chunk in enumerate(chunk_text(content)):
                content_hash = _sha(chunk)
                point_id = _point_id_from_source_hash(source_id, content_hash)
                if point_id in current_ids:
                    continue
                current_ids.add(point_id)
                if point_id in existing_ids:
                    unchanged_chunks += 1
                    continue

                payload = Payload(
                    node_type="text",
                    content=chunk,
                    content_hash=content_hash,
                    source_id=source_id,
                    chunk_index=idx,
                    hierarchy_path=source_id,
                    access_level=access_level,
                    text_metadata=TextMetadata(document_type=ext.lstrip(".")),
                    metadata=GlobalMetadata(last_modified=last_modified),
                )
                nodes_to_upsert.append(
                    VectorNode(
                        id=point_id,
                        vector=embedder.embed(chunk),
                        payload=payload,
                    )
                )
                new_chunks += 1

        elif ext in CODE_EXTS:
            lang = CODE_EXTS[ext]
            for idx, chunk in enumerate(chunk_code(content, language=lang)):
                content_hash = _sha(chunk.content)
                point_id = _point_id_from_source_hash(source_id, content_hash)
                if point_id in current_ids:
                    continue
                current_ids.add(point_id)
                if point_id in existing_ids:
                    unchanged_chunks += 1
                    continue

                payload = Payload(
                    node_type="code",
                    content=chunk.content,
                    content_hash=content_hash,
                    source_id=source_id,
                    chunk_index=idx,
                    hierarchy_path=f"{source_id} > {chunk.symbol_name}" if chunk.symbol_name else source_id,
                    access_level=access_level,
                    code_metadata=CodeMetadata(
                        language=lang,
                        ast_type=chunk.ast_type,
                        symbol_name=chunk.symbol_name,
                        line_start=chunk.line_start,
                        line_end=chunk.line_end,
                        parameters=chunk.parameters,
                        calls=chunk.calls,
                        docstring=chunk.docstring,
                    ),
                    metadata=GlobalMetadata(last_modified=last_modified),
                )
                nodes_to_upsert.append(
                    VectorNode(
                        id=point_id,
                        vector=embedder.embed(chunk.content),
                        payload=payload,
                    )
                )
                new_chunks += 1

        stale_ids = sorted(existing_ids - current_ids)
        stale_deleted += len(stale_ids)
        if stale_ids and not dry_run:
            store.delete_by_ids(stale_ids)

        if nodes_to_upsert and not dry_run:
            store.upsert(nodes_to_upsert)
            nodes_created += len(nodes_to_upsert)

        unchanged_count = len(current_ids.intersection(existing_ids))
        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        logger.info(
            json.dumps(
                {
                    "event": "ingest_summary",
                    "source_id": source_id,
                    "new_chunks": len(nodes_to_upsert),
                    "unchanged_chunks": unchanged_count,
                    "stale_deleted": len(stale_ids),
                    "skipped": 0,
                    "duration_ms": duration_ms,
                    "dry_run": dry_run,
                },
                ensure_ascii=True,
            )
        )

    return IngestResult(
        nodes_created=nodes_created,
        skipped=skipped,
        new_chunks=new_chunks,
        unchanged_chunks=unchanged_chunks,
        stale_deleted=stale_deleted,
    )


def ingest_urls(
    urls: list[str],
    store: QdrantStore,
    embedder: EmbeddingProvider,
    access_level: str = "internal",
    dry_run: bool = False,
    jina_reader_base_url: str = "https://r.jina.ai/",
    request_timeout_seconds: float = 45.0,
) -> IngestResult:
    nodes_created = 0
    skipped = 0
    new_chunks = 0
    unchanged_chunks = 0
    stale_deleted = 0

    valid_urls: list[str] = []
    for raw in urls:
        url = (raw or "").strip()
        if not url or not _is_http_url(url):
            skipped += 1
            continue
        valid_urls.append(url)

    if not valid_urls:
        return IngestResult(
            nodes_created=nodes_created,
            skipped=skipped,
            new_chunks=new_chunks,
            unchanged_chunks=unchanged_chunks,
            stale_deleted=stale_deleted,
        )

    store.ensure_collection()
    seen_sources: set[str] = set()
    for source_id in valid_urls:
        if source_id in seen_sources:
            continue
        seen_sources.add(source_id)
        started_at = time.perf_counter()
        try:
            raw = _fetch_web_content_via_jina(
                source_id,
                jina_reader_base_url=jina_reader_base_url,
                request_timeout_seconds=request_timeout_seconds,
            )
        except Exception as exc:
            logger.warning("ingest_url_fetch_failed source=%s error=%s", source_id, exc)
            skipped += 1
            continue

        content = sanitize_web_content(raw)
        if not content.strip():
            skipped += 1
            continue

        existing_ids = store.list_point_ids_by_source_id(source_id)
        current_ids: set[str] = set()
        nodes_to_upsert: list[VectorNode] = []
        now = datetime.now(timezone.utc)
        doc_type = _infer_web_document_type(source_id)

        for idx, chunk in enumerate(chunk_text(content)):
            content_hash = _sha(chunk)
            point_id = _point_id_from_source_hash(source_id, content_hash)
            if point_id in current_ids:
                continue
            current_ids.add(point_id)
            if point_id in existing_ids:
                unchanged_chunks += 1
                continue
            payload = Payload(
                node_type="text",
                content=chunk,
                content_hash=content_hash,
                source_id=source_id,
                chunk_index=idx,
                hierarchy_path=source_id,
                access_level=access_level,
                text_metadata=TextMetadata(document_type=doc_type),
                metadata=GlobalMetadata(last_modified=now),
            )
            nodes_to_upsert.append(
                VectorNode(
                    id=point_id,
                    vector=embedder.embed(chunk),
                    payload=payload,
                )
            )
            new_chunks += 1

        stale_ids = sorted(existing_ids - current_ids)
        stale_deleted += len(stale_ids)
        if stale_ids and not dry_run:
            store.delete_by_ids(stale_ids)
        if nodes_to_upsert and not dry_run:
            store.upsert(nodes_to_upsert)
            nodes_created += len(nodes_to_upsert)

        unchanged_count = len(current_ids.intersection(existing_ids))
        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        logger.info(
            json.dumps(
                {
                    "event": "ingest_summary",
                    "source_id": source_id,
                    "new_chunks": len(nodes_to_upsert),
                    "unchanged_chunks": unchanged_count,
                    "stale_deleted": len(stale_ids),
                    "skipped": 0,
                    "duration_ms": duration_ms,
                    "dry_run": dry_run,
                },
                ensure_ascii=True,
            )
        )

    return IngestResult(
        nodes_created=nodes_created,
        skipped=skipped,
        new_chunks=new_chunks,
        unchanged_chunks=unchanged_chunks,
        stale_deleted=stale_deleted,
    )
