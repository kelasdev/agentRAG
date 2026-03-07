from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from agentrag.config import Settings
from agentrag.planner import QueryPlan, build_query_plan
from agentrag.providers.embeddings import EmbeddingProvider
from agentrag.qdrant_store import QdrantStore
from agentrag.reranker import rerank
from agentrag.retrieval import retrieve_candidates
from agentrag.summarizer import summarize_context


@dataclass
class QueryPipelineResult:
    plan: QueryPlan
    hits: list[Any]
    compressed_context: str
    fallback_used: bool
    candidate_limit: int
    final_top_k: int


def run_query_pipeline(
    query: str,
    settings: Settings,
    embedder: EmbeddingProvider,
    store: QdrantStore,
    top_k: int | None = None,
    node_type: str | None = None,
    language: str | None = None,
    access_level: str | None = None,
) -> QueryPipelineResult:
    final_top_k = top_k or settings.final_top_k
    extracted_plan = build_query_plan(query)
    plan = QueryPlan(
        intent=extracted_plan.intent,
        node_type=node_type or extracted_plan.node_type,
        language=language or extracted_plan.language,
        symbol_name=extracted_plan.symbol_name,
        access_level=access_level or extracted_plan.access_level,
    )
    candidate_limit = settings.rerank_candidates if settings.enable_reranker else final_top_k
    desired_limit = max(candidate_limit, final_top_k)

    retrieval = retrieve_candidates(
        query=query,
        store=store,
        embedder=embedder,
        plan=plan,
        limit=desired_limit,
    )
    hits = retrieval.candidates
    fallback_used = False

    if settings.enable_reranker:
        hits = rerank(query=query, candidates=hits, top_k=final_top_k)
    else:
        hits = hits[:final_top_k]

    if not hits:
        relaxed_plan = QueryPlan(
            intent=plan.intent,
            node_type=node_type,
            language=language,
            symbol_name=plan.symbol_name,
            access_level=access_level or plan.access_level,
        )
        relaxed = retrieve_candidates(
            query=query,
            store=store,
            embedder=embedder,
            plan=relaxed_plan,
            limit=desired_limit,
        )
        hits = relaxed.candidates
        fallback_used = True
        if settings.enable_reranker:
            hits = rerank(query=query, candidates=hits, top_k=final_top_k)
        else:
            hits = hits[:final_top_k]

    return QueryPipelineResult(
        plan=plan,
        hits=hits,
        compressed_context=summarize_context(hits) if hits else "",
        fallback_used=fallback_used,
        candidate_limit=desired_limit,
        final_top_k=final_top_k,
    )
