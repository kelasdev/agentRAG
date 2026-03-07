import json
from types import SimpleNamespace

from typer.testing import CliRunner

import agentrag.cli as cli
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
    assert "does not exist" in res.stderr


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
    assert "is empty" in res.stderr
