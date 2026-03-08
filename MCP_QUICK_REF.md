# MCP Server Quick Reference

## Start Server

```bash
python -m agentrag.mcp_server
```

## Available Tools

### 1. query_memory

Search the RAG memory system.

**Parameters**:
- `query` (string, required) - Search query
- `top_k` (integer, default: 3) - Number of results
- `node_type` (string, optional) - Filter: "text" or "code"
- `language` (string, optional) - Filter by language (e.g., "python")
- `access_level` (string, default: "internal") - "public", "internal", or "admin"

**Example**:
```json
{
  "query": "python function example",
  "top_k": 5,
  "node_type": "code",
  "language": "python"
}
```

### 2. ingest_documents

Add documents to memory.

**Parameters**:
- `targets` (array, required) - File paths, directories, or URLs
- `access_level` (string, default: "internal") - Access level
- `dry_run` (boolean, default: false) - Preview without writing

**Example**:
```json
{
  "targets": [
    "/path/to/file.py",
    "https://example.com/doc"
  ],
  "access_level": "internal",
  "dry_run": false
}
```

### 3. health_check

Check system health.

**Parameters**: None

**Example**:
```json
{}
```

## Test Commands

```bash
# Unit tests
pytest tests/test_mcp_server.py -v

# Integration test
python scripts/test_mcp_integration.py

# CLI equivalent
agentrag health
agentrag query "test" --top-k 3
agentrag ingest test_data/ --dry-run
```

## Response Format

All tools return JSON via `CallToolResult`:

```json
{
  "content": [
    {
      "type": "text",
      "text": "{...json response...}"
    }
  ],
  "isError": false
}
```

## Error Handling

Errors return:
```json
{
  "content": [
    {
      "type": "text",
      "text": "Error: <message>"
    }
  ],
  "isError": true
}
```

## Configuration

Set in `.env`:
```env
QDRANT_URL=https://xyz.cloud.qdrant.io
QDRANT_API_KEY=your_key
COLLECTION_NAME=agentrag_memory_fastembed
EMBEDDING_PROVIDER=fastembed
EMBEDDING_MODEL=jinaai/jina-embeddings-v2-base-code
```
