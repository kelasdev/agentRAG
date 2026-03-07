from __future__ import annotations

import re
from qdrant_client.models import ScoredPoint


TOKEN_RE = re.compile(r"[a-zA-Z0-9_]+")


def rerank(query: str, candidates: list[ScoredPoint], top_k: int) -> list[ScoredPoint]:
    query_tokens = set(_tokens(query))
    if not query_tokens:
        return candidates[:top_k]

    def score(hit: ScoredPoint) -> float:
        payload = hit.payload or {}
        content = str(payload.get("content", ""))
        overlap = len(query_tokens.intersection(_tokens(content)))
        # Blend lexical overlap and vector score for stable ranking.
        return (0.3 * float(hit.score)) + (0.7 * overlap)

    return sorted(candidates, key=score, reverse=True)[:top_k]


def _tokens(text: str) -> set[str]:
    return {m.group(0).lower() for m in TOKEN_RE.finditer(text)}
