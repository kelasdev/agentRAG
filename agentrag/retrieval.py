from __future__ import annotations

from dataclasses import dataclass

from qdrant_client.models import ScoredPoint

from agentrag.planner import QueryPlan
from agentrag.providers.embeddings import EmbeddingProvider
from agentrag.qdrant_store import QdrantStore


@dataclass
class RetrievalResult:
    candidates: list[ScoredPoint]
    plan: QueryPlan


def retrieve_candidates(
    query: str,
    store: QdrantStore,
    embedder: EmbeddingProvider,
    plan: QueryPlan,
    limit: int,
) -> RetrievalResult:
    query_vector = embedder.embed(query)
    candidates = store.search(
        query_vector=query_vector,
        limit=limit,
        node_type=plan.node_type,
        language=plan.language,
        symbol_name=plan.symbol_name,
        access_level=plan.access_level,
    )
    return RetrievalResult(candidates=candidates, plan=plan)
