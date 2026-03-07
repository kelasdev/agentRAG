from agentrag.providers.embeddings import EmbeddingProvider


def test_unsupported_provider_fails_fast():
    try:
        EmbeddingProvider(provider="openrouter")
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "Unsupported embedding provider" in str(exc)


def test_llama_provider_requires_model_path():
    try:
        EmbeddingProvider(provider="llama_cpp_python", model_path=None)
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "LLAMA_CPP_EMBED_MODEL_PATH" in str(exc)
