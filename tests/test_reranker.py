from types import SimpleNamespace

from agentrag.reranker import rerank


def test_rerank_prioritizes_token_overlap():
    candidates = [
        SimpleNamespace(score=0.9, payload={"content": "random unrelated text"}),
        SimpleNamespace(score=0.1, payload={"content": "python qdrant upsert function example"}),
    ]
    ranked = rerank("python upsert function", candidates, top_k=1)
    assert "upsert" in ranked[0].payload["content"]
