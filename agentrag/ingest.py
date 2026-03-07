from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from agentrag.chunkers.code import chunk_code
from agentrag.chunkers.text import chunk_text
from agentrag.models import CodeMetadata, GlobalMetadata, Payload, TextMetadata, VectorNode
from agentrag.providers.embeddings import EmbeddingProvider
from agentrag.qdrant_store import QdrantStore

TEXT_EXTS = {".md", ".txt", ".rst"}
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


@dataclass
class IngestResult:
    nodes_created: int
    skipped: int
    new_chunks: int
    unchanged_chunks: int
    stale_deleted: int


def _read_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


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

    return IngestResult(
        nodes_created=nodes_created,
        skipped=skipped,
        new_chunks=new_chunks,
        unchanged_chunks=unchanged_chunks,
        stale_deleted=stale_deleted,
    )
