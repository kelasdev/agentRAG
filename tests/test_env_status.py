from types import SimpleNamespace

from typer.testing import CliRunner

import agentrag.cli as cli


def test_env_status_ok(monkeypatch):
    runner = CliRunner()
    class _DummyEmbedder:
        dimensions = 768

    monkeypatch.setattr(
        cli,
        "get_settings",
        lambda: SimpleNamespace(
            qdrant_url="http://localhost:6333",
            qdrant_api_key="",
            collection_name="agentrag_memory",
            embedding_provider="llama_cpp_python",
            embedding_model="nomic-embed",
            llama_cpp_embed_model_path="/home/kelasdev/models/nomic-embed-text-v2-moe.Q4_K_M.gguf",
            llama_cpp_n_threads=4,
            final_top_k=3,
        ),
    )
    monkeypatch.setattr(cli, "_build_embedder_or_exit", lambda settings: _DummyEmbedder())

    res = runner.invoke(cli.app, ["env-status"])
    assert res.exit_code == 0
    assert '"ok": true' in res.stdout
