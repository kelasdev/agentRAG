"""Test for MCP Server."""

import asyncio
import json
import logging
from typing import Any, Dict

import pytest
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import CallToolRequest, CallToolResult, ListToolsRequest

from agentrag.mcp_server import server
from agentrag.config import get_settings
from agentrag.providers.embeddings import EmbeddingProvider
from agentrag.qdrant_store import QdrantStore

logger = logging.getLogger(__name__)


@pytest.fixture
def mock_server():
    """Create a mock MCP server instance."""
    return server


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    class MockSettings:
        qdrant_url = "http://localhost:6333"
        qdrant_api_key = "test_key"
        collection_name = "test_collection"
        embedding_provider = "fastembed"
        embedding_model = "jinaai/jina-embeddings-v2-base-code"
        llama_cpp_embed_model_path = None
        llama_cpp_n_threads = 4
        openai_compatible_base_url = None
        openai_compatible_api_key = None
        embedding_request_timeout_seconds = 30.0
        jina_reader_base_url = "https://r.jina.ai/"
        web_fetch_timeout_seconds = 45.0
        final_top_k = 3
    
    return MockSettings()


@pytest.fixture
def mock_embedder(mock_settings):
    """Create a mock embedding provider."""
    return EmbeddingProvider(
        provider=mock_settings.embedding_provider,
        model_name=mock_settings.embedding_model,
        model_path=mock_settings.llama_cpp_embed_model_path,
        n_threads=mock_settings.llama_cpp_n_threads,
        openai_base_url=mock_settings.openai_compatible_base_url,
        openai_api_key=mock_settings.openai_compatible_api_key,
        request_timeout_seconds=mock_settings.embedding_request_timeout_seconds,
    )


@pytest.fixture
def mock_store(mock_settings, mock_embedder):
    """Create a mock Qdrant store."""
    return QdrantStore(
        url=mock_settings.qdrant_url,
        api_key=mock_settings.qdrant_api_key,
        collection_name=mock_settings.collection_name,
        vector_size=mock_embedder.dimensions,
    )


@pytest.mark.skip(reason="MCP server tests require proper server setup")
async def test_list_tools(mock_server):
    """Test listing available tools."""
    request = ListToolsRequest()
    response = await mock_server.list_tools()
    
    assert isinstance(response, list)
    assert len(response) > 0
    
    # Check for required tools
    tool_names = {tool.name for tool in response}
    assert "query_memory" in tool_names
    assert "ingest_documents" in tool_names
    assert "health_check" in tool_names


@pytest.mark.skip(reason="MCP server tests require proper server setup")
async def test_call_tool_query_memory(mock_server, mock_embedder, mock_store):
    """Test calling query_memory tool."""
    arguments = {
        "query": "test query",
        "top_k": 3
    }
    
    request = CallToolRequest(name="query_memory", arguments=arguments)
    response = await mock_server.call_tool(request.name, request.arguments)
    
    assert isinstance(response, CallToolResult)
    assert isinstance(response.content, list)
    assert len(response.content) == 1
    assert isinstance(response.content[0], dict)


@pytest.mark.skip(reason="MCP server tests require proper server setup")
async def test_call_tool_ingest_documents(mock_server, mock_embedder, mock_store):
    """Test calling ingest_documents tool."""
    arguments = {
        "targets": ["test.txt", "https://example.com"],
        "access_level": "internal",
        "dry_run": True
    }
    
    request = CallToolRequest(name="ingest_documents", arguments=arguments)
    response = await mock_server.call_tool(request.name, request.arguments)
    
    assert isinstance(response, CallToolResult)
    assert isinstance(response.content, list)
    assert len(response.content) == 1
    assert isinstance(response.content[0], dict)


@pytest.mark.skip(reason="MCP server tests require proper server setup")
async def test_call_tool_health_check(mock_server, mock_embedder, mock_store):
    """Test calling health_check tool."""
    arguments = {}
    
    request = CallToolRequest(name="health_check", arguments=arguments)
    response = await mock_server.call_tool(request.name, request.arguments)
    
    assert isinstance(response, CallToolResult)
    assert isinstance(response.content, list)
    assert len(response.content) == 1
    assert isinstance(response.content[0], dict)


@pytest.mark.skip(reason="MCP server tests require proper server setup")
async def test_mcp_server_initialization():
    """Test MCP server initialization."""
    # This test ensures the server can be initialized without errors
    try:
        from mcp.server import Server
        from mcp.server.stdio import stdio_server
        
        # Create a test server instance
        test_server = Server("test_agentrag")
        
        # Test tool registration
        @test_server.list_tools()
        async def list_tools() -> list:
            return []
        
        # Test tool call
        @test_server.call_tool()
        async def call_tool(name: str, arguments: dict) -> dict:
            return {"ok": True, "name": name, "arguments": arguments}
        
        # Test basic functionality
        tools = await test_server.list_tools()
        assert isinstance(tools, list)
        
        result = await test_server.call_tool("test", {"key": "value"})
        assert result["ok"] is True
        assert result["name"] == "test"
        assert result["arguments"] == {"key": "value"}
        
    except ImportError:
        pytest.skip("mcp library not available")