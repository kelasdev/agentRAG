from __future__ import annotations

from pathlib import Path

import typer

from agentrag.config import get_settings
from agentrag.ingest import ingest_paths
from agentrag.pipeline import run_query_pipeline
from agentrag.providers.embeddings import EmbeddingProvider
from agentrag.qdrant_store import QdrantStore

app = typer.Typer(no_args_is_help=True)


@app.command("ingest")
def ingest_command(
    path: list[Path] = typer.Argument(..., exists=False),
    collection: str | None = typer.Option(None, help="Qdrant collection name"),
    access_level: str = typer.Option("internal", help="public/internal/admin"),
    dry_run: bool = typer.Option(False, help="Compute ingest delta without writing to Qdrant"),
) -> None:
    settings = get_settings()
    collection_name = collection or settings.collection_name
    embedder = EmbeddingProvider()
    store = QdrantStore(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
        collection_name=collection_name,
        vector_size=embedder.dimensions,
    )

    files: list[Path] = []
    for p in path:
        if p.is_dir():
            files.extend(x for x in p.rglob("*") if x.is_file())
        else:
            files.append(p)

    result = ingest_paths(
        files,
        store=store,
        embedder=embedder,
        access_level=access_level,
        dry_run=dry_run,
    )
    if dry_run:
        typer.echo(
            "Dry run completed. "
            f"new_chunks={result.new_chunks} unchanged={result.unchanged_chunks} "
            f"stale={result.stale_deleted} skipped={result.skipped}"
        )
        return

    typer.echo(
        "Ingest completed. "
        f"nodes_created={result.nodes_created} new_chunks={result.new_chunks} "
        f"unchanged={result.unchanged_chunks} stale_deleted={result.stale_deleted} skipped={result.skipped}"
    )


@app.command("query")
def query_command(
    q: str = typer.Argument(..., help="Query text"),
    collection: str | None = typer.Option(None, help="Qdrant collection name"),
    top_k: int | None = typer.Option(None, help="Number of final results"),
    node_type: str | None = typer.Option(None, help="Filter by node type: text/code"),
    language: str | None = typer.Option(None, help="Filter by code language, e.g. python"),
    access_level: str | None = typer.Option(None, help="Filter by access level"),
    show_plan: bool = typer.Option(False, help="Show extracted query plan"),
) -> None:
    settings = get_settings()
    collection_name = collection or settings.collection_name
    embedder = EmbeddingProvider()
    store = QdrantStore(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
        collection_name=collection_name,
        vector_size=embedder.dimensions,
    )
    result = run_query_pipeline(
        query=q,
        settings=settings,
        embedder=embedder,
        store=store,
        top_k=top_k,
        node_type=node_type,
        language=language,
        access_level=access_level,
    )
    results = result.hits

    if not results:
        typer.echo("No results found.")
        raise typer.Exit(0)

    if show_plan:
        typer.echo(
            "Plan: "
            f"intent={result.plan.intent} node_type={result.plan.node_type} "
            f"language={result.plan.language} access_level={result.plan.access_level} "
            f"candidate_limit={result.candidate_limit} final_top_k={result.final_top_k} "
            f"fallback_used={result.fallback_used}"
        )

    for i, hit in enumerate(results, start=1):
        payload = hit.payload or {}
        content = str(payload.get("content", "")).strip().replace("\n", " ")
        preview = content[:160] + ("..." if len(content) > 160 else "")
        source_id = payload.get("source_id", "-")
        hpath = payload.get("hierarchy_path", "-")
        typer.echo(
            f"[{i}] score={hit.score:.4f} source={source_id} hierarchy={hpath}\n"
            f"    {preview}"
        )
    typer.echo("\nCompressed Context:")
    typer.echo(result.compressed_context)


@app.command("health")
def health_command(collection: str | None = typer.Option(None, help="Qdrant collection name")) -> None:
    settings = get_settings()
    embedder = EmbeddingProvider()
    store = QdrantStore(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
        collection_name=collection or settings.collection_name,
        vector_size=embedder.dimensions,
    )
    ok = store.health_check()
    typer.echo(f"qdrant_ok={str(ok).lower()} collection={store.collection_name}")
    if not ok:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
