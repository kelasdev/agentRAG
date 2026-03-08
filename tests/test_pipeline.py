from types import SimpleNamespace

from agentrag.pipeline import run_query_pipeline


class FakeEmbedder:
    def embed(self, _text: str):
        return [0.1, 0.2, 0.3]


class FakeStore:
    def __init__(self):
        self.calls = []

    def search(
        self,
        query_vector,
        limit,
        node_type=None,
        language=None,
        symbol_name=None,
        access_level=None,
    ):
        self.calls.append(
            {
                "limit": limit,
                "node_type": node_type,
                "language": language,
                "symbol_name": symbol_name,
                "access_level": access_level,
            }
        )
        # First call with strict filters returns empty. Relaxed fallback returns one hit.
        if node_type == "code" and language == "python":
            return []
        return [
            SimpleNamespace(
                score=0.5,
                payload={
                    "source_id": "PRD.md",
                    "hierarchy_path": "PRD.md",
                    "content": "qdrant upsert function via API",
                },
            )
        ]


def test_pipeline_fallback_relaxes_constraints():
    settings = SimpleNamespace(final_top_k=3)
    store = FakeStore()
    result = run_query_pipeline(
        query="show python function for qdrant upsert",
        settings=settings,  # type: ignore[arg-type]
        embedder=FakeEmbedder(),  # type: ignore[arg-type]
        store=store,  # type: ignore[arg-type]
    )
    assert result.fallback_used is True
    assert len(result.hits) == 1
    assert len(store.calls) == 2


def test_pipeline_passes_symbol_name_filter():
    settings = SimpleNamespace(final_top_k=3)
    store = FakeStore()
    run_query_pipeline(
        query="explain function calculate_roi",
        settings=settings,  # type: ignore[arg-type]
        embedder=FakeEmbedder(),  # type: ignore[arg-type]
        store=store,  # type: ignore[arg-type]
    )
    assert store.calls[0]["symbol_name"] == "calculate_roi"
