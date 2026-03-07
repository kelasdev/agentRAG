from types import SimpleNamespace

from agentrag.reranker import rerank


class _FakeEmbedder:
    def embed(self, text: str):
        if text == "query":
            return [1.0, 0.0]
        if "relevant" in text:
            return [0.9, 0.1]
        return [0.0, 1.0]


def test_rerank_uses_embedding_similarity():
    candidates = [
        SimpleNamespace(score=0.9, payload={"content": "random unrelated text"}),
        SimpleNamespace(score=0.1, payload={"content": "this is relevant to query"}),
    ]
    ranked = rerank("query", candidates, top_k=1, embedder=_FakeEmbedder())
    assert "relevant" in ranked[0].payload["content"]
