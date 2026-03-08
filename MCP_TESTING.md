# MCP Server Testing Guide

## Overview

The agentRAG MCP server provides three main tools for AI agents:
- `query_memory` - Search the RAG memory system
- `ingest_documents` - Add documents to memory
- `health_check` - Verify system health

## Running Tests

### Unit Tests

Run the automated test suite:

```bash
pytest tests/test_mcp_server.py -v
```

Expected output:
```
tests/test_mcp_server.py::test_health_check PASSED
tests/test_mcp_server.py::test_query_memory_validation PASSED
tests/test_mcp_server.py::test_ingest_validation PASSED
```

### Integration Tests

Run the manual integration test:

```bash
python scripts/test_mcp_integration.py
```

This tests:
1. Health check functionality
2. Document ingestion (dry run)
3. Query memory with real data

## Manual Testing with MCP Inspector

The MCP Inspector is a visual tool for testing MCP servers interactively.

### Install MCP Inspector

```bash
npm install -g @modelcontextprotocol/inspector
```

### Start the MCP Server

```bash
cd /home/kelasdev/agentRAG
source .venv/bin/activate
python -m agentrag.mcp_server
```

### Connect with Inspector

In another terminal:

```bash
mcp-inspector python -m agentrag.mcp_server
```

This opens a web interface where you can:
- View available tools
- Test tool calls with custom parameters
- See request/response JSON

## Testing Individual Tools

### 1. Health Check

**Purpose**: Verify Qdrant connection and embedder status

**Test Command**:
```bash
python -c "
import asyncio
import json
from agentrag.mcp_server import _handle_health_check
from agentrag.config import get_settings
from agentrag.providers.embeddings import EmbeddingProvider
from agentrag.qdrant_store import QdrantStore

async def test():
    settings = get_settings()
    embedder = EmbeddingProvider(
        provider=settings.embedding_provider,
        model_name=settings.embedding_model,
    )
    store = QdrantStore(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
        collection_name=settings.collection_name,
        vector_size=embedder.dimensions,
    )
    result = await _handle_health_check(embedder, store)
    print(result.content[0].text)

asyncio.run(test())
"
```

**Expected Response**:
```json
{
  "ok": true,
  "qdrant_ok": true,
  "embedder_ok": true,
  "collection_exists": true,
  "collection_points": 22,
  "collection_name": "agentrag_memory_fastembed",
  "embedding_provider": "fastembed",
  "embedding_dimensions": 768
}
```

### 2. Query Memory

**Purpose**: Search for relevant information in the memory system

**Test via CLI**:
```bash
agentrag query "python example" --top-k 3
```

**MCP Tool Parameters**:
```json
{
  "query": "python example",
  "top_k": 3,
  "node_type": "code",
  "language": "python",
  "access_level": "internal"
}
```

**Expected Response**:
```json
{
  "query": "python example",
  "total_hits": 3,
  "fallback_used": false,
  "final_top_k": 3,
  "hits": [
    {
      "rank": 0.8234,
      "source_id": "/path/to/file.py",
      "hierarchy_path": "module.function",
      "content": "def example():\n    ...",
      "node_type": "code",
      "score": 0.8234,
      "language": "python",
      "symbol_name": "example"
    }
  ]
}
```

### 3. Ingest Documents

**Purpose**: Add new documents to the memory system

**Test via CLI (Dry Run)**:
```bash
agentrag ingest test_data/README.md --dry-run
```

**MCP Tool Parameters**:
```json
{
  "targets": ["test_data/README.md", "https://example.com/doc"],
  "access_level": "internal",
  "dry_run": true
}
```

**Expected Response**:
```json
{
  "nodes_created": 0,
  "skipped": 0,
  "new_chunks": 3,
  "unchanged_chunks": 0,
  "stale_deleted": 1,
  "dry_run": true
}
```

## Testing with Kiro CLI

If you have Kiro CLI configured with the agentRAG MCP server:

### Configure MCP Server

Add to your Kiro CLI config (`~/.kiro/mcp.json`):

```json
{
  "mcpServers": {
    "agentrag": {
      "command": "python",
      "args": ["-m", "agentrag.mcp_server"],
      "cwd": "/home/kelasdev/agentRAG",
      "env": {
        "PYTHONPATH": "/home/kelasdev/agentRAG"
      }
    }
  }
}
```

### Test in Kiro CLI

```bash
kiro-cli chat
```

Then in the chat:
```
> Use agentrag to search for "python examples"
> Use agentrag to check system health
> Use agentrag to ingest test_data/README.md
```

## Validation Tests

### Input Validation

The server validates all inputs:

**Empty Query**:
```python
# Should raise ValueError
await _handle_query_memory({"query": ""}, embedder, store)
```

**Empty Targets**:
```python
# Should raise ValueError
await _handle_ingest_documents({"targets": []}, embedder, store)
```

**Invalid Node Type**:
```python
# Should be filtered by schema validation
{"query": "test", "node_type": "invalid"}
```

## Performance Testing

### Query Performance

Test query response time:

```bash
time agentrag query "test query" --top-k 10
```

Expected: < 2 seconds for typical queries

### Ingest Performance

Test ingestion speed:

```bash
time agentrag ingest test_data/ --dry-run
```

Expected: ~1-2 seconds per file (dry run)

## Troubleshooting

### Server Won't Start

**Check Python environment**:
```bash
which python
python --version  # Should be 3.12+
```

**Check dependencies**:
```bash
pip list | grep mcp
```

Should show:
- mcp
- mcp-server-stdio

### Connection Errors

**Check Qdrant**:
```bash
agentrag health
```

**Check environment variables**:
```bash
cat .env | grep QDRANT
```

### Tool Call Failures

**Enable debug logging**:
```bash
export LOG_LEVEL=DEBUG
python -m agentrag.mcp_server
```

**Check error messages** in the CallToolResult:
```json
{
  "content": [{"type": "text", "text": "Error: ..."}],
  "isError": true
}
```

## CI/CD Integration

Add to your CI pipeline:

```yaml
- name: Test MCP Server
  run: |
    source .venv/bin/activate
    pytest tests/test_mcp_server.py -v
    python scripts/test_mcp_integration.py
```

## Next Steps

1. Test with real AI agent (Claude, GPT-4, etc.)
2. Monitor performance in production
3. Add custom tools for your use case
4. Implement authentication if needed
