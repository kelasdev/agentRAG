from __future__ import annotations

import math
from qdrant_client.models import ScoredPoint

def rerank(
    query: str,
    candidates: list[ScoredPoint],
    top_k: int,
    embedder: object,
) -> list[ScoredPoint]:
    if not candidates:
        return candidates[:top_k]
    query_vec = _embed_text(embedder, query)

    def score(hit: ScoredPoint) -> float:
        payload = hit.payload or {}
        content = str(payload.get("content", ""))
        doc_vec = _embed_text(embedder, content)
        return _cosine_similarity(query_vec, doc_vec)

    return sorted(candidates, key=score, reverse=True)[:top_k]


def _embed_text(embedder: object, text: str) -> list[float]:
    raw = getattr(embedder, "embed")(text)
    return [float(x) for x in raw]


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    size = min(len(a), len(b))
    if size == 0:
        return 0.0
    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0
    for i in range(size):
        x = a[i]
        y = b[i]
        dot += x * y
        norm_a += x * x
        norm_b += y * y
    denom = math.sqrt(norm_a) * math.sqrt(norm_b)
    if denom == 0:
        return 0.0
    return dot / denom
