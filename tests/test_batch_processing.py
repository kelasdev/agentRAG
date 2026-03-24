"""Test for embedding batch processing."""

import importlib.util
import pytest
from unittest.mock import Mock, patch

from agentrag.providers.embeddings import EmbeddingProvider


@pytest.fixture
def mock_fastembed():
    """Mock fastembed provider."""
    class MockFastembed:
        def embed(self, texts):
            return [[len(text)] * 768 for text in texts]
    
    return MockFastembed()


@pytest.fixture
def mock_openai_compatible():
    """Mock openai compatible provider."""
    class MockOpenAICompatible:
        def __init__(self):
            self._client = Mock()
        
        def _openai_embed_batch(self, texts):
            return [[len(text)] * 768 for text in texts]
    
    return MockOpenAICompatible()


@pytest.fixture
def mock_llama_cpp():
    """Mock llama cpp provider."""
    class MockLlamaCpp:
        def __init__(self):
            self._llama = Mock()
        
        def create_embedding(self, text):
            return {"data": [{"embedding": [len(text)] * 768}]}
    
    return MockLlamaCpp()


@pytest.fixture
def mock_provider_fastembed(mock_fastembed):
    """Create mock provider for fastembed."""
    if importlib.util.find_spec("fastembed") is None:
        pytest.skip("fastembed is not installed in this environment")
    return EmbeddingProvider(
        provider="fastembed",
        model_name="BAAI/bge-small-en-v1.5",
        model_path=None,
        n_threads=4,
        openai_base_url=None,
        openai_api_key=None,
        request_timeout_seconds=30.0,
    )


@pytest.fixture
def mock_provider_openai_compatible(mock_openai_compatible):
    """Create mock provider for openai compatible."""
    pytest.skip("Requires running OpenAI-compatible server")


@pytest.fixture
def mock_provider_llama_cpp(mock_llama_cpp):
    """Create mock provider for llama cpp."""
    pytest.skip("Requires llama.cpp model file")


@pytest.mark.asyncio
async def test_embed_batch_fastembed(mock_provider_fastembed):
    """Test batch processing for fastembed provider."""
    texts = ["hello", "world", "test"]
    
    # Mock the fastembed embed method
    with patch.object(mock_provider_fastembed, '_fastembed', new_callable=Mock) as mock_embed:
        mock_embed.embed.return_value = [[len(text)] * 768 for text in texts]
        
        result = mock_provider_fastembed.embed_batch(texts)
        
        assert len(result) == 3
        assert len(result[0]) == 768
        assert len(result[1]) == 768
        assert len(result[2]) == 768
        assert result[0][0] == 5  # length of "hello"
        assert result[1][0] == 5  # length of "world"
        assert result[2][0] == 4  # length of "test"


@pytest.mark.asyncio
async def test_embed_batch_openai_compatible(mock_provider_openai_compatible):
    """Test batch processing for openai compatible provider."""
    texts = ["hello", "world", "test"]
    
    # Mock the openai embed batch method
    with patch.object(mock_provider_openai_compatible, '_openai_http_client', new_callable=Mock) as mock_client:
        mock_client.post.return_value.json.return_value = {
            "data": [
                {"embedding": [len(text)] * 768},
                {"embedding": [len(text)] * 768},
                {"embedding": [len(text)] * 768}
            ]
        }
        
        result = mock_provider_openai_compatible.embed_batch(texts)
        
        assert len(result) == 3
        assert len(result[0]) == 768
        assert len(result[1]) == 768
        assert len(result[2]) == 768
        assert result[0][0] == 5  # length of "hello"
        assert result[1][0] == 5  # length of "world"
        assert result[2][0] == 4  # length of "test"


@pytest.mark.asyncio
async def test_embed_batch_llama_cpp(mock_provider_llama_cpp):
    """Test batch processing for llama cpp provider."""
    texts = ["hello", "world", "test"]
    
    # Mock the llama cpp create_embedding method
    with patch.object(mock_provider_llama_cpp, '_llama', new_callable=Mock) as mock_llama:
        mock_llama.create_embedding.side_effect = [
            {"data": [{"embedding": [len(text)] * 768}]},
            {"data": [{"embedding": [len(text)] * 768}]},
            {"data": [{"embedding": [len(text)] * 768}]}
        ]
        
        result = mock_provider_llama_cpp.embed_batch(texts)
        
        assert len(result) == 3
        assert len(result[0]) == 768
        assert len(result[1]) == 768
        assert len(result[2]) == 768
        assert result[0][0] == 5  # length of "hello"
        assert result[1][0] == 5  # length of "world"
        assert result[2][0] == 4  # length of "test"


@pytest.mark.asyncio
async def test_embed_batch_empty_input(mock_provider_fastembed):
    """Test batch processing with empty input."""
    result = mock_provider_fastembed.embed_batch([])
    assert result == []


@pytest.mark.asyncio
async def test_embed_batch_single_input(mock_provider_fastembed):
    """Test batch processing with single input."""
    result = mock_provider_fastembed.embed_batch(["hello"])
    assert len(result) == 1
    assert len(result[0]) > 0


@pytest.mark.asyncio
async def test_embed_batch_large_input(mock_provider_fastembed):
    """Test batch processing with large input."""
    texts = ["test"] * 100
    result = mock_provider_fastembed.embed_batch(texts)
    
    assert len(result) == 100
    assert len(result[0]) > 0


@pytest.mark.asyncio
async def test_embed_batch_error_handling(mock_provider_fastembed):
    """Test error handling in batch processing."""
    # Mock embed to raise an error
    with patch.object(mock_provider_fastembed, '_fastembed') as mock_embed:
        mock_embed.embed.side_effect = Exception("Test error")
        
        with pytest.raises(Exception):
            mock_provider_fastembed.embed_batch(["test1", "test2", "test3"])


@pytest.mark.asyncio
async def test_embed_batch_logging(mock_provider_fastembed):
    """Test logging in batch processing."""
    texts = ["hello", "world"]
    
    # Mock the logger
    with patch("agentrag.providers.embeddings.logger") as mock_logger:
        result = mock_provider_fastembed.embed_batch(texts)
        
        # Verify logging was called
        mock_logger.debug.assert_called()
        # Just verify the log was called with the right format string
        assert mock_logger.debug.call_count > 0
