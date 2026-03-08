import json
from types import SimpleNamespace

from typer.testing import CliRunner

import agentrag.cli as cli
from agentrag.ingest import IngestResult
from agentrag.pipeline import QueryPipelineResult
from agentrag.planner import QueryPlan


class _DummyEmbedder:
    def __init__(self, *args, **kwargs):
        self.dimensions = 8


class _DummyStore:
    def __init__(self, *args, **kwargs):
        pass


def test_query_command_outputs_json(monkeypatch):
    runner = CliRunner()

    monkeypatch.setattr(
        cli,
        "get_settings",
        lambda: SimpleNamespace(
            qdrant_url="http://localhost:6333",
            qdrant_api_key="",
            collection_name="agentrag_memory",
            embedding_provider="llama_cpp_python",
            embedding_model="dummy",
            llama_cpp_embed_model_path=None,
            llama_cpp_n_threads=4,
        ),
    )
    monkeypatch.setattr(cli, "EmbeddingProvider", _DummyEmbedder)
    monkeypatch.setattr(cli, "QdrantStore", _DummyStore)
    monkeypatch.setattr(cli, "_preflight_query_collection", lambda **kwargs: None)
    monkeypatch.setattr(cli, "_check_embedding_collection_dimension", lambda **kwargs: (True, "ok"))

    fake_result = QueryPipelineResult(
        plan=QueryPlan(
            intent="explain_function",
            node_type="code",
            language="python",
            symbol_name="calculate_roi",
            access_level="internal",
        ),
        hits=[
            SimpleNamespace(
                score=0.91,
                payload={
                    "source_id": "src/a.py",
                    "hierarchy_path": "src/a.py > calculate_roi",
                    "content": "def calculate_roi(gain, cost): return (gain-cost)/cost",
                },
            )
        ],
        fallback_used=False,
        candidate_limit=20,
        final_top_k=3,
    )

    monkeypatch.setattr(cli, "run_query_pipeline", lambda **kwargs: fake_result)

    res = runner.invoke(cli.app, ["query", "show python function calculate_roi"])
    assert res.exit_code == 0
    parsed = json.loads(res.stdout)
    assert parsed["query"] == "show python function calculate_roi"
    assert parsed["plan"]["symbol_name"] == "calculate_roi"
    assert len(parsed["hits"]) == 1


def test_query_preflight_fails_when_collection_missing(monkeypatch):
    runner = CliRunner()

    monkeypatch.setattr(
        cli,
        "get_settings",
        lambda: SimpleNamespace(
            qdrant_url="http://localhost:6333",
            qdrant_api_key="",
            collection_name="agentrag_memory",
            embedding_provider="llama_cpp_python",
            embedding_model="dummy",
            llama_cpp_embed_model_path=None,
            llama_cpp_n_threads=4,
        ),
    )

    class _Collection:
        def __init__(self, name):
            self.name = name

    class _CollectionsResponse:
        def __init__(self):
            self.collections = [_Collection("other_collection")]

    class _Client:
        def __init__(self, *args, **kwargs):
            pass

        def get_collections(self):
            return _CollectionsResponse()

    monkeypatch.setattr(cli, "QdrantClient", _Client)
    res = runner.invoke(cli.app, ["query", "hello"])

    assert res.exit_code == 1
    err = json.loads(res.stderr)
    assert err["error"]["code"] == "QDRANT_PREFLIGHT_FAILED"
    assert "does not exist" in err["error"]["message"]


def test_query_preflight_fails_when_collection_empty(monkeypatch):
    runner = CliRunner()

    monkeypatch.setattr(
        cli,
        "get_settings",
        lambda: SimpleNamespace(
            qdrant_url="http://localhost:6333",
            qdrant_api_key="",
            collection_name="agentrag_memory",
            embedding_provider="llama_cpp_python",
            embedding_model="dummy",
            llama_cpp_embed_model_path=None,
            llama_cpp_n_threads=4,
        ),
    )

    class _Collection:
        def __init__(self, name):
            self.name = name

    class _CollectionsResponse:
        def __init__(self):
            self.collections = [_Collection("agentrag_memory")]

    class _CountResponse:
        def __init__(self, count):
            self.count = count

    class _Client:
        def __init__(self, *args, **kwargs):
            pass

        def get_collections(self):
            return _CollectionsResponse()

        def count(self, *args, **kwargs):
            return _CountResponse(0)

    monkeypatch.setattr(cli, "QdrantClient", _Client)
    res = runner.invoke(cli.app, ["query", "hello"])

    assert res.exit_code == 1
    err = json.loads(res.stderr)
    assert err["error"]["code"] == "QDRANT_PREFLIGHT_FAILED"
    assert "is empty" in err["error"]["message"]


def test_query_preflight_fails_when_dimension_mismatch(monkeypatch):
    runner = CliRunner()

    monkeypatch.setattr(
        cli,
        "get_settings",
        lambda: SimpleNamespace(
            qdrant_url="http://localhost:6333",
            qdrant_api_key="",
            collection_name="agentrag_memory",
            embedding_provider="llama_cpp_python",
            embedding_model="dummy",
            llama_cpp_embed_model_path=None,
            llama_cpp_n_threads=4,
        ),
    )
    monkeypatch.setattr(cli, "EmbeddingProvider", _DummyEmbedder)
    monkeypatch.setattr(cli, "_preflight_query_collection", lambda **kwargs: None)
    monkeypatch.setattr(
        cli,
        "_check_embedding_collection_dimension",
        lambda **kwargs: (False, "embedding dimension mismatch: model_dim=768 collection_dim=384"),
    )

    res = runner.invoke(cli.app, ["query", "hello"])
    assert res.exit_code == 1
    err = json.loads(res.stderr)
    assert err["error"]["code"] == "DIMENSION_PREFLIGHT_FAILED"
    assert "embedding dimension mismatch" in err["error"]["message"]


def test_query_handles_qdrant_dimension_error_with_friendly_message(monkeypatch):
    runner = CliRunner()

    monkeypatch.setattr(
        cli,
        "get_settings",
        lambda: SimpleNamespace(
            qdrant_url="http://localhost:6333",
            qdrant_api_key="",
            collection_name="agentrag_memory",
            embedding_provider="llama_cpp_python",
            embedding_model="dummy",
            llama_cpp_embed_model_path=None,
            llama_cpp_n_threads=4,
        ),
    )
    monkeypatch.setattr(cli, "EmbeddingProvider", _DummyEmbedder)
    monkeypatch.setattr(cli, "QdrantStore", _DummyStore)
    monkeypatch.setattr(cli, "_preflight_query_collection", lambda **kwargs: None)
    monkeypatch.setattr(cli, "_check_embedding_collection_dimension", lambda **kwargs: (True, "ok"))
    monkeypatch.setattr(
        cli,
        "run_query_pipeline",
        lambda **kwargs: (_ for _ in ()).throw(
            Exception("Wrong input: Vector dimension error: expected dim: 4096, got 768")
        ),
    )

    res = runner.invoke(cli.app, ["query", "hello"])
    assert res.exit_code == 1
    err = json.loads(res.stderr)
    assert err["error"]["code"] == "VECTOR_DIMENSION_MISMATCH"
    assert err["error"]["details"]["collection"] == "agentrag_memory"


def test_ingest_command_accepts_url_and_merges_results(monkeypatch):
    runner = CliRunner()
    monkeypatch.setattr(
        cli,
        "get_settings",
        lambda: SimpleNamespace(
            qdrant_url="http://localhost:6333",
            qdrant_api_key="",
            collection_name="agentrag_memory",
            embedding_provider="llama_cpp_python",
            embedding_model="dummy",
            llama_cpp_embed_model_path=None,
            llama_cpp_n_threads=4,
            enable_dimension_preflight=False,
            jina_reader_base_url="https://r.jina.ai/",
            web_fetch_timeout_seconds=45.0,
        ),
    )
    monkeypatch.setattr(cli, "_check_qdrant", lambda **kwargs: (True, "ok", 0))
    monkeypatch.setattr(cli, "EmbeddingProvider", _DummyEmbedder)
    monkeypatch.setattr(cli, "QdrantStore", _DummyStore)
    monkeypatch.setattr(
        cli,
        "ingest_paths",
        lambda *args, **kwargs: IngestResult(
            nodes_created=1, skipped=0, new_chunks=1, unchanged_chunks=0, stale_deleted=0
        ),
    )
    monkeypatch.setattr(
        cli,
        "ingest_urls",
        lambda *args, **kwargs: IngestResult(
            nodes_created=2, skipped=0, new_chunks=2, unchanged_chunks=0, stale_deleted=0
        ),
    )

    res = runner.invoke(cli.app, ["ingest", "https://example.com/doc.pdf"])
    assert res.exit_code == 0
    assert "nodes_created=3" in res.stdout
    assert "new_chunks=3" in res.stdout
