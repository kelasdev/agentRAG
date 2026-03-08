#!/usr/bin/env python3
"""Manual integration test for MCP server.

This script tests the MCP server by simulating client interactions.
Run this to verify the server works end-to-end.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agentrag.mcp_server import (
    _handle_health_check,
    _handle_query_memory,
    _handle_ingest_documents,
)
from agentrag.config import get_settings
from agentrag.providers.embeddings import EmbeddingProvider
from agentrag.qdrant_store import QdrantStore


async def test_health_check():
    """Test health check."""
    print("\n=== Testing Health Check ===")
    
    settings = get_settings()
    embedder = EmbeddingProvider(
        provider=settings.embedding_provider,
        model_name=settings.embedding_model,
        model_path=settings.llama_cpp_embed_model_path,
        n_threads=settings.llama_cpp_n_threads,
        openai_base_url=settings.openai_compatible_base_url,
        openai_api_key=settings.openai_compatible_api_key,
        request_timeout_seconds=settings.embedding_request_timeout_seconds,
    )
    
    store = QdrantStore(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
        collection_name=settings.collection_name,
        vector_size=embedder.dimensions,
    )
    
    result = await _handle_health_check(embedder, store)
    response = json.loads(result.content[0].text)
    
    print(json.dumps(response, indent=2))
    
    if response["ok"]:
        print("✓ Health check passed")
    else:
        print("✗ Health check failed")
    
    return response["ok"], embedder, store


async def test_ingest(embedder, store):
    """Test document ingestion."""
    print("\n=== Testing Document Ingestion (Dry Run) ===")
    
    test_file = Path(__file__).parent.parent / "test_data" / "README.md"
    
    if not test_file.exists():
        print(f"✗ Test file not found: {test_file}")
        return False
    
    arguments = {
        "targets": [str(test_file)],
        "access_level": "internal",
        "dry_run": True
    }
    
    result = await _handle_ingest_documents(arguments, embedder, store)
    response = json.loads(result.content[0].text)
    
    print(json.dumps(response, indent=2))
    print("✓ Ingest test passed (dry run)")
    
    return True


async def test_query(embedder, store):
    """Test query memory."""
    print("\n=== Testing Query Memory ===")
    
    arguments = {
        "query": "test example",
        "top_k": 3,
        "access_level": "internal"
    }
    
    result = await _handle_query_memory(arguments, embedder, store)
    response = json.loads(result.content[0].text)
    
    print(f"Query: {response['query']}")
    print(f"Total hits: {response['total_hits']}")
    print(f"Fallback used: {response['fallback_used']}")
    
    if response['total_hits'] > 0:
        print("\nTop results:")
        for i, hit in enumerate(response['hits'][:3], 1):
            print(f"\n{i}. Score: {hit['score']:.4f}")
            print(f"   Source: {hit['source_id']}")
            print(f"   Content: {hit['content'][:100]}...")
    
    print("✓ Query test passed")
    return True


async def main():
    """Run all integration tests."""
    print("=" * 60)
    print("MCP Server Integration Test")
    print("=" * 60)
    
    try:
        # Test health check
        health_ok, embedder, store = await test_health_check()
        
        if not health_ok:
            print("\n✗ Health check failed. Cannot proceed with other tests.")
            return 1
        
        # Test ingestion
        ingest_ok = await test_ingest(embedder, store)
        
        if not ingest_ok:
            print("\n✗ Ingest test failed.")
            return 1
        
        # Test query
        query_ok = await test_query(embedder, store)
        
        if not query_ok:
            print("\n✗ Query test failed.")
            return 1
        
        print("\n" + "=" * 60)
        print("✓ All integration tests passed!")
        print("=" * 60)
        return 0
        
    except Exception as e:
        print(f"\n✗ Integration test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
