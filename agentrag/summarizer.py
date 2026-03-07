from __future__ import annotations

from qdrant_client.models import ScoredPoint


def summarize_context(hits: list[ScoredPoint], max_chars_per_item: int = 220) -> str:
    lines: list[str] = []
    for i, hit in enumerate(hits, start=1):
        payload = hit.payload or {}
        source_id = payload.get("source_id", "-")
        hierarchy = payload.get("hierarchy_path", "-")
        content = str(payload.get("content", "")).replace("\n", " ").strip()
        preview = content[:max_chars_per_item]
        if len(content) > max_chars_per_item:
            preview += "..."
        lines.append(f"{i}. [{source_id}] {hierarchy} | {preview}")
    return "\n".join(lines)
