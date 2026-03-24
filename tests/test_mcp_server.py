"""Test for MCP Server."""

import json
import os
import pytest
from agentrag.mcp_server import (
    _handle_health_check,
    _handle_query_memory,
    _handle_ingest_documents,
)
from agentrag.config import get_settings
from agentrag.providers.embeddings import EmbeddingProvider
from agentrag.qdrant_store import QdrantStore


# These tests exercise MCP handlers that depend on a real configured environment
# (QDRANT_URL + embedding runtime). Skip when not configured.
if not os.getenv("QDRANT_URL"):
    pytest.skip("QDRANT_URL is not set; skipping MCP server integration-style tests", allow_module_level=True)


@pytest.fixture
def embedder():
    """Create embedding provider."""
    settings = get_settings()
    return EmbeddingProvider(
        provider=settings.embedding_provider,
        model_name=settings.embedding_model,
        model_path=settings.llama_cpp_embed_model_path,
        n_threads=settings.llama_cpp_n_threads,
        openai_base_url=settings.openai_compatible_base_url,
        openai_api_key=settings.openai_compatible_api_key,
        request_timeout_seconds=settings.embedding_request_timeout_seconds,
    )


@pytest.fixture
def store(embedder):
    """Create Qdrant store."""
    settings = get_settings()
    return QdrantStore(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
        collection_name=settings.collection_name,
        vector_size=embedder.dimensions,
    )


@pytest.mark.asyncio
async def test_health_check(embedder, store):
    """Test health_check handler."""
    result = await _handle_health_check(embedder, store)
    
    assert result
    assert len(result) == 1
    
    response = json.loads(result[0].text)
    assert "ok" in response
    assert "qdrant_ok" in response
    assert "embedder_ok" in response
    assert "collection_exists" in response
    assert "collection_name" in response


@pytest.mark.asyncio
async def test_query_memory_validation(embedder, store):
    """Test query_memory with invalid input."""
    with pytest.raises(ValueError, match="cannot be empty"):
        await _handle_query_memory({"query": ""}, embedder, store)


@pytest.mark.asyncio
async def test_ingest_validation(embedder, store):
    """Test ingest_documents with invalid input."""
    with pytest.raises(ValueError, match="cannot be empty"):
        await _handle_ingest_documents({"targets": []}, embedder, store)
