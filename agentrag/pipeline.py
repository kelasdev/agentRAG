from __future__ import annotations

from dataclasses import dataclass
import json
import logging
import time
from typing import Any
from uuid import uuid4

from agentrag.config import Settings
from agentrag.planner import QueryPlan, build_query_plan
from agentrag.providers.embeddings import EmbeddingProvider
from agentrag.qdrant_store import QdrantStore
from agentrag.retrieval import retrieve_candidates

logger = logging.getLogger(__name__)


@dataclass
class QueryPipelineResult:
    plan: QueryPlan
    hits: list[Any]
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
    query_id = str(uuid4())
    final_top_k = top_k or settings.final_top_k
    extracted_plan = build_query_plan(query)
    plan = QueryPlan(
        intent=extracted_plan.intent,
        node_type=node_type or extracted_plan.node_type,
        language=language or extracted_plan.language,
        symbol_name=extracted_plan.symbol_name,
        access_level=access_level or extracted_plan.access_level,
    )
    desired_limit = final_top_k

    strict_started = time.perf_counter()
    retrieval = retrieve_candidates(
        query=query,
        store=store,
        embedder=embedder,
        plan=plan,
        limit=desired_limit,
    )
    hits = retrieval.candidates
    fallback_used = False
    fallback_stage_hit: str | None = None
    _log_query_stage(
        query_id=query_id,
        stage="strict",
        candidate_count=len(hits),
        duration_ms=round((time.perf_counter() - strict_started) * 1000, 2),
        filters={
            "node_type": plan.node_type,
            "language": plan.language,
            "symbol_name": plan.symbol_name,
            "access_level": plan.access_level,
        },
    )

    hits = hits[:final_top_k]

    if not hits:
        fallback_used = True
        fallback_plans = [
            QueryPlan(
                intent=plan.intent,
                node_type=plan.node_type,
                language=None,
                symbol_name=plan.symbol_name,
                access_level=access_level or plan.access_level,
            ),
            QueryPlan(
                intent=plan.intent,
                node_type=node_type,
                language=language,
                symbol_name=None,
                access_level=access_level or plan.access_level,
            ),
        ]
        for idx, relaxed_plan in enumerate(fallback_plans, start=1):
            stage_name = f"fallback_{idx}"
            stage_started = time.perf_counter()
            relaxed = retrieve_candidates(
                query=query,
                store=store,
                embedder=embedder,
                plan=relaxed_plan,
                limit=desired_limit,
            )
            hits = relaxed.candidates
            _log_query_stage(
                query_id=query_id,
                stage=stage_name,
                candidate_count=len(hits),
                duration_ms=round((time.perf_counter() - stage_started) * 1000, 2),
                filters={
                    "node_type": relaxed_plan.node_type,
                    "language": relaxed_plan.language,
                    "symbol_name": relaxed_plan.symbol_name,
                    "access_level": relaxed_plan.access_level,
                },
            )
            if hits:
                fallback_stage_hit = stage_name
                break
        hits = hits[:final_top_k]

    constraint_match = _constraints_match(plan, hits)
    logger.info(
        json.dumps(
            {
                "event": "query_outcome",
                "query_id": query_id,
                "fallback_used": fallback_used,
                "fallback_stage_hit": fallback_stage_hit,
                "final_top_k": final_top_k,
                "constraint_match": constraint_match,
            },
            ensure_ascii=True,
        )
    )
    return QueryPipelineResult(
        plan=plan,
        hits=hits,
        fallback_used=fallback_used,
        candidate_limit=desired_limit,
        final_top_k=final_top_k,
    )


def _log_query_stage(
    query_id: str,
    stage: str,
    candidate_count: int,
    duration_ms: float,
    filters: dict[str, Any],
) -> None:
    logger.info(
        json.dumps(
            {
                "event": "query_stage",
                "query_id": query_id,
                "stage": stage,
                "candidate_count": candidate_count,
                "duration_ms": duration_ms,
                "filters": filters,
            },
            ensure_ascii=True,
        )
    )


def _constraints_match(plan: QueryPlan, hits: list[Any]) -> bool:
    if not hits:
        return False
    for hit in hits:
        payload = hit.payload or {}
        code_meta = payload.get("code_metadata") or {}
        if plan.node_type and payload.get("node_type") != plan.node_type:
            continue
        if plan.language and code_meta.get("language") != plan.language:
            continue
        if plan.symbol_name and code_meta.get("symbol_name") != plan.symbol_name:
            continue
        if plan.access_level and payload.get("access_level") != plan.access_level:
            continue
        return True
    return False
