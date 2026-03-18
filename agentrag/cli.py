from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlparse

import typer
from qdrant_client import QdrantClient

from agentrag.config import get_settings
from agentrag.ingest import IngestResult, ingest_paths, ingest_urls
from agentrag.pipeline import run_query_pipeline
from agentrag.providers.embeddings import EmbeddingProvider
from agentrag.qdrant_store import QdrantStore

app = typer.Typer(no_args_is_help=True)


def _json_error_and_exit(
    code: str,
    message: str,
    details: dict[str, object] | None = None,
    exit_code: int = 1,
) -> None:
    error_payload: dict[str, object] = {"code": code, "message": message}
    if details:
        error_payload["details"] = details
    payload = {"ok": False, "error": error_payload}
    typer.echo(json.dumps(payload, ensure_ascii=True, indent=2), err=True)
    raise typer.Exit(code=exit_code)


def _resolve_qdrant_api_key(url: str, api_key: str) -> str | None:
    # Ignore api key for local development endpoints.
    from urllib.parse import urlparse

    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if host in {"localhost", "127.0.0.1", "::1"}:
        return None
    return api_key or None


def _preflight_query_collection(
    qdrant_url: str,
    qdrant_api_key: str,
    collection_name: str,
    timeout_seconds: float = 2.0,
) -> None:
    ok, message, _ = _check_qdrant(
        qdrant_url=qdrant_url,
        qdrant_api_key=qdrant_api_key,
        collection_name=collection_name,
        timeout_seconds=timeout_seconds,
        require_collection=True,
        require_non_empty=True,
    )
    if not ok:
        _json_error_and_exit(
            code="QDRANT_PREFLIGHT_FAILED",
            message=message,
            details={"collection": collection_name},
        )


def _check_qdrant(
    qdrant_url: str,
    qdrant_api_key: str,
    collection_name: str,
    timeout_seconds: float = 2.0,
    require_collection: bool = False,
    require_non_empty: bool = False,
) -> tuple[bool, str, int | None]:
    client = QdrantClient(
        url=qdrant_url,
        api_key=_resolve_qdrant_api_key(qdrant_url, qdrant_api_key),
        timeout=timeout_seconds,
    )
    try:
        collections = client.get_collections().collections
    except Exception as exc:
        return (
            False,
            f"URL is not reachable within {timeout_seconds:.1f}s at {qdrant_url}. error={exc}",
            None,
        )

    names = {c.name for c in collections}
    if require_collection and collection_name not in names:
        return False, f"collection '{collection_name}' does not exist.", None

    if require_non_empty:
        try:
            count_response = client.count(collection_name=collection_name, exact=False)
            points_count = int(getattr(count_response, "count", 0) or 0)
        except Exception as exc:
            return (
                False,
                f"unable to check collection size for '{collection_name}'. error={exc}",
                None,
            )
        if points_count == 0:
            return False, f"collection '{collection_name}' is empty. Run ingest first.", points_count
        return True, "ok", points_count

    return True, "ok", None


def _extract_collection_vector_size(vectors_config: Any) -> int | None:
    # Handles common qdrant-client shapes:
    # - VectorParams(size=...)
    # - {"default": VectorParams(...)} / {"default": {"size": ...}}
    size = getattr(vectors_config, "size", None)
    if size is not None:
        return int(size)
    if isinstance(vectors_config, Mapping):
        if not vectors_config:
            return None
        first = next(iter(vectors_config.values()))
        named_size = getattr(first, "size", None)
        if named_size is not None:
            return int(named_size)
        if isinstance(first, Mapping) and first.get("size") is not None:
            return int(first["size"])
    return None


def _check_embedding_collection_dimension(
    qdrant_url: str,
    qdrant_api_key: str,
    collection_name: str,
    embed_dimensions: int,
    allow_missing_collection: bool,
    timeout_seconds: float = 2.0,
) -> tuple[bool, str]:
    client = QdrantClient(
        url=qdrant_url,
        api_key=_resolve_qdrant_api_key(qdrant_url, qdrant_api_key),
        timeout=timeout_seconds,
    )
    try:
        collections = client.get_collections().collections
    except Exception as exc:
        return False, f"unable to reach qdrant for dimension check. error={exc}"

    names = {c.name for c in collections}
    if collection_name not in names:
        if allow_missing_collection:
            return True, "collection_missing_will_be_created"
        return False, f"collection '{collection_name}' does not exist."

    try:
        info = client.get_collection(collection_name=collection_name)
    except Exception as exc:
        return False, f"unable to read collection '{collection_name}' config. error={exc}"

    vectors_config = getattr(getattr(info, "config", None), "params", None)
    vectors_config = getattr(vectors_config, "vectors", None)
    existing_size = _extract_collection_vector_size(vectors_config)
    if existing_size is None:
        return False, f"unable to determine vector size for collection '{collection_name}'."

    if int(embed_dimensions) != int(existing_size):
        return (
            False,
            (
                "embedding dimension mismatch: "
                f"model_dim={embed_dimensions} collection_dim={existing_size} "
                f"collection='{collection_name}'. "
                "Use a new collection or recreate this collection and re-ingest."
            ),
        )
    return True, "ok"


def _build_embedder_or_exit(settings: object) -> EmbeddingProvider:
    try:
        return EmbeddingProvider(
            provider=str(getattr(settings, "embedding_provider", "")),
            model_name=getattr(settings, "embedding_model", None),
            model_path=getattr(settings, "llama_cpp_embed_model_path", None),
            n_threads=int(getattr(settings, "llama_cpp_n_threads", 4)),
            openai_base_url=getattr(settings, "openai_compatible_base_url", None),
            openai_api_key=getattr(settings, "openai_compatible_api_key", None),
            request_timeout_seconds=float(
                getattr(settings, "embedding_request_timeout_seconds", 30.0)
            ),
        )
    except Exception as exc:
        _json_error_and_exit(
            code="EMBEDDING_PREFLIGHT_FAILED",
            message=str(exc),
            details={
                "provider": str(getattr(settings, "embedding_provider", "")),
                "model": str(getattr(settings, "embedding_model", "")),
                "path": str(getattr(settings, "llama_cpp_embed_model_path", "")),
                "base_url": str(getattr(settings, "openai_compatible_base_url", "")),
            },
        )


def _raise_friendly_dimension_error(collection_name: str, exc: Exception, code: str) -> None:
    message = str(exc)
    normalized = message.lower()
    if "Vector dimension error" in message and "expected dim" in message and "got" in message:
        _json_error_and_exit(
            code="VECTOR_DIMENSION_MISMATCH",
            message="Embedding dimension does not match collection vector size.",
            details={
                "collection": collection_name,
                "raw_error": message,
                "action": "use new collection or recreate and re-ingest",
            },
        )
    if "timeout" in normalized or "timed out" in normalized:
        _json_error_and_exit(
            code="RUNTIME_TIMEOUT",
            message="Operation timed out while processing request.",
            details={"collection": collection_name, "raw_error": message},
        )
    if "connection" in normalized or "connect" in normalized:
        _json_error_and_exit(
            code="RUNTIME_CONNECTIVITY_FAILED",
            message="Connection failed while processing request.",
            details={"collection": collection_name, "raw_error": message},
        )
    _json_error_and_exit(
        code=code,
        message="Runtime error while processing request.",
        details={"collection": collection_name, "raw_error": message},
    )


def _collect_files_respecting_gitignore(root: Path) -> list[Path]:
    """Collect files from directory, respecting .gitignore patterns.

    IMPORTANT: do not use Path.rglob() + post-filtering because it still traverses
    ignored directories (e.g. .venv, node_modules) and becomes extremely heavy.
    We instead walk top-down and prune ignored dirs early.
    """
    import fnmatch
    import os

    root = root.resolve()
    gitignore_path = root / ".gitignore"

    # Always exclude VCS metadata directories.
    raw_patterns: list[str] = [".git/"]

    if gitignore_path.exists():
        with open(gitignore_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                raw_patterns.append(line)

    def _norm_pattern(p: str) -> str:
        # Keep patterns close to gitignore format, but normalize separators.
        return p.strip().replace("\\", "/")

    patterns = [_norm_pattern(p) for p in raw_patterns if _norm_pattern(p)]

    def _matches_pattern(rel_posix: str, parts: tuple[str, ...], pattern: str, *, is_dir: bool) -> bool:
        # Minimal gitignore-like matcher:
        # - lines starting with '!' negate (unignore)
        # - trailing '/' means directory-only
        # - patterns without '/' match a single path component name (file or directory)
        # - patterns with '/' match against the relative POSIX path
        pat = pattern
        if pat.startswith("!"):
            pat = pat[1:]
        pat = pat.strip()
        if not pat:
            return False

        anchored = pat.startswith("/")
        if anchored:
            pat = pat.lstrip("/")

        dir_only = pat.endswith("/")
        pat_core = pat.rstrip("/")

        if not pat_core:
            return False

        has_slash = "/" in pat_core

        # Directory matching (for pruning)
        if is_dir:
            # If pattern has no '/', gitignore matches basename anywhere.
            if not has_slash:
                return any(fnmatch.fnmatch(part, pat_core) for part in parts)
            # If it has '/', treat it as a path match (anchored to root by default in our implementation).
            if anchored:
                return fnmatch.fnmatch(rel_posix, pat_core)
            return fnmatch.fnmatch(rel_posix, pat_core) or fnmatch.fnmatch(rel_posix, f"*/{pat_core}")

        # File matching
        if dir_only:
            # A directory-only rule does not directly match files (it matches via pruning the dir).
            return False
        if not has_slash:
            # Basename match anywhere.
            return fnmatch.fnmatch(parts[-1] if parts else rel_posix, pat_core)
        if anchored:
            return fnmatch.fnmatch(rel_posix, pat_core)
        return fnmatch.fnmatch(rel_posix, pat_core) or fnmatch.fnmatch(rel_posix, f"*/{pat_core}")

    def _is_ignored(relative: Path, *, is_dir: bool) -> bool:
        rel_posix = relative.as_posix()
        parts = tuple(relative.parts)
        ignored = False
        for p in patterns:
            is_negation = p.startswith("!")
            matched = _matches_pattern(rel_posix, parts, p, is_dir=is_dir)
            if not matched:
                continue
            ignored = not is_negation
        return ignored

    files: list[Path] = []

    # Top-down walk so we can prune ignored directories early.
    for dirpath, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        current_dir = Path(dirpath)
        rel_dir = current_dir.relative_to(root)

        # Prune ignored directories in-place to avoid traversing them.
        # This is the main fix for "folder indexing becomes too heavy".
        for d in list(dirnames):
            rel_child = (rel_dir / d) if str(rel_dir) != "." else Path(d)
            if _is_ignored(rel_child, is_dir=True):
                dirnames.remove(d)

        for name in filenames:
            rel_file = (rel_dir / name) if str(rel_dir) != "." else Path(name)
            if _is_ignored(rel_file, is_dir=False):
                continue
            files.append(current_dir / name)

    return files


@app.command("ingest")
def ingest_command(
    target: list[str] = typer.Argument(..., help="Path/dir or URL (http/https)"),
    collection: str | None = typer.Option(None, help="Qdrant collection name"),
    access_level: str = typer.Option("internal", help="public/internal/admin"),
    dry_run: bool = typer.Option(False, help="Compute ingest delta without writing to Qdrant"),
) -> None:
    settings = get_settings()
    collection_name = collection or settings.collection_name
    ok, message, _ = _check_qdrant(
        qdrant_url=settings.qdrant_url,
        qdrant_api_key=settings.qdrant_api_key,
        collection_name=collection_name,
        timeout_seconds=2.0,
        require_collection=False,
        require_non_empty=False,
    )
    if not ok:
        _json_error_and_exit(
            code="QDRANT_PREFLIGHT_FAILED",
            message=message,
            details={"collection": collection_name},
        )

    embedder = _build_embedder_or_exit(settings)
    if bool(getattr(settings, "enable_dimension_preflight", True)):
        dim_ok, dim_message = _check_embedding_collection_dimension(
            qdrant_url=settings.qdrant_url,
            qdrant_api_key=settings.qdrant_api_key,
            collection_name=collection_name,
            embed_dimensions=embedder.dimensions,
            allow_missing_collection=True,
            timeout_seconds=2.0,
        )
        if not dim_ok:
            _json_error_and_exit(
                code="DIMENSION_PREFLIGHT_FAILED",
                message=dim_message,
                details={"collection": collection_name, "embed_dimensions": embedder.dimensions},
            )
    store = QdrantStore(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
        collection_name=collection_name,
        vector_size=embedder.dimensions,
    )

    files: list[Path] = []
    urls: list[str] = []
    for raw in target:
        value = (raw or "").strip()
        parsed = urlparse(value)
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            urls.append(value)
            continue
        p = Path(value)
        if p.is_dir():
            files.extend(_collect_files_respecting_gitignore(p))
        else:
            files.append(p)

    try:
        files_result = ingest_paths(
            files,
            store=store,
            embedder=embedder,
            access_level=access_level,
            dry_run=dry_run,
        )
        urls_result = ingest_urls(
            urls,
            store=store,
            embedder=embedder,
            access_level=access_level,
            dry_run=dry_run,
            jina_reader_base_url=str(getattr(settings, "jina_reader_base_url", "https://r.jina.ai/")),
            request_timeout_seconds=float(getattr(settings, "web_fetch_timeout_seconds", 45.0)),
        )
        result = IngestResult(
            nodes_created=files_result.nodes_created + urls_result.nodes_created,
            skipped=files_result.skipped + urls_result.skipped,
            new_chunks=files_result.new_chunks + urls_result.new_chunks,
            unchanged_chunks=files_result.unchanged_chunks + urls_result.unchanged_chunks,
            stale_deleted=files_result.stale_deleted + urls_result.stale_deleted,
        )
    except Exception as exc:
        _raise_friendly_dimension_error(collection_name, exc, code="INGEST_RUNTIME_FAILED")
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
) -> None:
    settings = get_settings()
    collection_name = collection or settings.collection_name
    _preflight_query_collection(
        qdrant_url=settings.qdrant_url,
        qdrant_api_key=settings.qdrant_api_key,
        collection_name=collection_name,
    )
    embedder = _build_embedder_or_exit(settings)
    if bool(getattr(settings, "enable_dimension_preflight", True)):
        dim_ok, dim_message = _check_embedding_collection_dimension(
            qdrant_url=settings.qdrant_url,
            qdrant_api_key=settings.qdrant_api_key,
            collection_name=collection_name,
            embed_dimensions=embedder.dimensions,
            allow_missing_collection=False,
            timeout_seconds=2.0,
        )
        if not dim_ok:
            _json_error_and_exit(
                code="DIMENSION_PREFLIGHT_FAILED",
                message=dim_message,
                details={"collection": collection_name, "embed_dimensions": embedder.dimensions},
            )
    store = QdrantStore(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
        collection_name=collection_name,
        vector_size=embedder.dimensions,
    )
    try:
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
    except Exception as exc:
        _raise_friendly_dimension_error(collection_name, exc, code="QUERY_RUNTIME_FAILED")
    results = result.hits
    out_hits: list[dict[str, object]] = []
    for i, hit in enumerate(results, start=1):
        payload = hit.payload or {}
        content = str(payload.get("content", "")).strip()
        out_hits.append(
            {
                "rank": i,
                "score": float(hit.score),
                "source_id": payload.get("source_id"),
                "hierarchy_path": payload.get("hierarchy_path"),
                "content_preview": content[:160] + ("..." if len(content) > 160 else ""),
                "payload": payload,
            }
        )

    response = {
        "query": q,
        "plan": {
            "intent": result.plan.intent,
            "node_type": result.plan.node_type,
            "language": result.plan.language,
            "symbol_name": result.plan.symbol_name,
            "access_level": result.plan.access_level,
        },
        "fallback_used": result.fallback_used,
        "candidate_limit": result.candidate_limit,
        "final_top_k": result.final_top_k,
        "hits": out_hits,
    }
    typer.echo(json.dumps(response, ensure_ascii=True, indent=2))


@app.command("health")
def health_command(collection: str | None = typer.Option(None, help="Qdrant collection name")) -> None:
    settings = get_settings()
    collection_name = collection or settings.collection_name
    embedder_ok = True
    embedder_error = ""
    try:
        _ = _build_embedder_or_exit(settings)
    except typer.Exit:
        embedder_ok = False
        embedder_error = "embedding model failed to initialize"

    qdrant_ok, qdrant_message, points_count = _check_qdrant(
        qdrant_url=settings.qdrant_url,
        qdrant_api_key=settings.qdrant_api_key,
        collection_name=collection_name,
        timeout_seconds=2.0,
        require_collection=True,
        require_non_empty=False,
    )
    payload = {
        "ok": qdrant_ok and embedder_ok,
        "qdrant_ok": qdrant_ok,
        "qdrant_message": qdrant_message,
        "collection": collection_name,
        "collection_points": points_count,
        "embedding_ok": embedder_ok,
        "embedding_provider": settings.embedding_provider,
        "embedding_model": settings.embedding_model,
        "embedding_error": embedder_error,
    }
    typer.echo(json.dumps(payload, ensure_ascii=True, indent=2))
    if not payload["ok"]:
        raise typer.Exit(code=1)


@app.command("env-status")
def env_status_command() -> None:
    settings = get_settings()
    checks: list[dict[str, object]] = []
    embedding_runtime: dict[str, object] | None = None

    def add_check(
        name: str,
        ok: bool,
        value: object | None = None,
        fail_error: str | None = None,
    ) -> None:
        entry: dict[str, object | None] = {
            "name": name,
            "ok": ok,
            "value": value,
        }
        if not ok and fail_error:
            entry["error"] = fail_error
        checks.append(entry)

    add_check("QDRANT_URL", bool(settings.qdrant_url.strip()), settings.qdrant_url, "must be non-empty")
    add_check(
        "COLLECTION_NAME",
        bool(settings.collection_name.strip()),
        settings.collection_name,
        "must be non-empty",
    )
    add_check(
        "EMBEDDING_PROVIDER",
        settings.embedding_provider in {"llama_cpp_python", "fastembed", "openai_compatible"},
        settings.embedding_provider,
        "must be one of: llama_cpp_python, fastembed, openai_compatible",
    )
    add_check(
        "EMBEDDING_MODEL",
        bool(str(getattr(settings, "embedding_model", "") or "").strip()),
        getattr(settings, "embedding_model", ""),
        "must be non-empty",
    )
    if settings.embedding_provider == "llama_cpp_python":
        embed_path = settings.llama_cpp_embed_model_path or ""
        add_check(
            "LLAMA_CPP_EMBED_MODEL_PATH",
            bool(embed_path) and Path(embed_path).exists(),
            embed_path,
            "file must exist",
        )
        add_check(
            "LLAMA_CPP_N_THREADS",
            settings.llama_cpp_n_threads > 0,
            settings.llama_cpp_n_threads,
            "must be > 0",
        )
    if settings.embedding_provider == "openai_compatible":
        base_url = (settings.openai_compatible_base_url or "").strip()
        add_check(
            "OPENAI_COMPATIBLE_BASE_URL",
            bool(base_url),
            base_url,
            "must be non-empty for provider=openai_compatible",
        )
    add_check(
        "EMBEDDING_REQUEST_TIMEOUT_SECONDS",
        float(getattr(settings, "embedding_request_timeout_seconds", 30.0)) > 0.0,
        getattr(settings, "embedding_request_timeout_seconds", 30.0),
        "must be > 0",
    )
    add_check(
        "JINA_READER_BASE_URL",
        bool(str(getattr(settings, "jina_reader_base_url", "https://r.jina.ai/")).strip()),
        getattr(settings, "jina_reader_base_url", "https://r.jina.ai/"),
        "must be non-empty",
    )
    add_check(
        "WEB_FETCH_TIMEOUT_SECONDS",
        float(getattr(settings, "web_fetch_timeout_seconds", 45.0)) > 0.0,
        getattr(settings, "web_fetch_timeout_seconds", 45.0),
        "must be > 0",
    )
    add_check(
        "ENABLE_DIMENSION_PREFLIGHT",
        isinstance(getattr(settings, "enable_dimension_preflight", True), bool),
        getattr(settings, "enable_dimension_preflight", True),
        "must be boolean",
    )
    try:
        embedder = _build_embedder_or_exit(settings)
        embedding_runtime = {"provider": settings.embedding_provider}
        if settings.embedding_provider == "llama_cpp_python":
            embedding_runtime["model_path"] = getattr(settings, "llama_cpp_embed_model_path", "")
            embedding_runtime["n_threads"] = int(getattr(settings, "llama_cpp_n_threads", 0))
        elif settings.embedding_provider == "openai_compatible":
            embedding_runtime["model"] = getattr(settings, "embedding_model", "")
            embedding_runtime["base_url"] = getattr(settings, "openai_compatible_base_url", "")
        else:
            embedding_runtime["model"] = getattr(settings, "embedding_model", "")
        embedding_runtime["dimensions"] = int(getattr(embedder, "dimensions", 0) or 0)
        add_check("EMBEDDING_MODEL_INIT", True, getattr(settings, "embedding_model", ""))
        add_check(
            "EMBEDDING_DIMENSIONS",
            embedding_runtime["dimensions"] > 0,
            embedding_runtime["dimensions"],
            "must be > 0",
        )
    except typer.Exit:
        embedding_runtime = {"provider": settings.embedding_provider, "dimensions": 0}
        if settings.embedding_provider == "llama_cpp_python":
            embedding_runtime["model_path"] = getattr(settings, "llama_cpp_embed_model_path", "")
        elif settings.embedding_provider == "openai_compatible":
            embedding_runtime["model"] = getattr(settings, "embedding_model", "")
            embedding_runtime["base_url"] = getattr(settings, "openai_compatible_base_url", "")
        else:
            embedding_runtime["model"] = getattr(settings, "embedding_model", "")
        checks.append(
            {
                "name": "EMBEDDING_MODEL_INIT",
                "ok": False,
                "value": getattr(settings, "embedding_model", ""),
                "error": "failed to initialize embedding model",
            }
        )
        checks.append(
            {
                "name": "EMBEDDING_DIMENSIONS",
                "ok": False,
                "value": 0,
                "error": "unable to detect dimensions",
            }
        )

    ok = all(bool(c["ok"]) for c in checks)
    failed = [c for c in checks if not bool(c["ok"])]
    payload = {
        "ok": ok,
        "embedding_runtime": embedding_runtime,
        "passed": {str(c.get("name")): c.get("value") for c in checks if bool(c.get("ok"))},
        "failed": {
            str(c.get("name")): c.get("error", "check failed")
            for c in checks
            if not bool(c.get("ok"))
        },
    }
    typer.echo(json.dumps(payload, ensure_ascii=True, indent=2))
    if not ok:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
