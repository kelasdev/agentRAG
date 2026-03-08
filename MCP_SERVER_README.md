# MCP Server Documentation

## Overview
MCP (Model Context Protocol) Server untuk agentRAG yang memungkinkan integrasi dengan AI agents seperti Claude, Kiro, dan lainnya.

## Installation

### Prerequisites
- Python 3.10+
- Qdrant Cloud account
- MCP client (VS Code, Codex, KiloCode, dll)
- Understanding of [vector dimensions](docs/VECTOR_DIMENSIONS.md) (recommended)

### Install Dependencies
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

## Configuration

### Environment Variables
Buat file `.env` dengan konfigurasi berikut:

```env
QDRANT_URL=https://qdrant.geekscodebase.me
QDRANT_API_KEY=your_qdrant_api_key_here
COLLECTION_NAME=agentrag_memory
EMBEDDING_PROVIDER=fastembed
EMBEDDING_MODEL=jinaai/jina-embeddings-v2-base-code
FINAL_TOP_K=3
```

### MCP Client Configuration

#### VS Code
Edit file `settings.json`:

```json
{
  "mcpServers": {
    "agentrag": {
      "command": "uv",
      "args": [
        "run",
        "python",
        "-m",
        "agentrag.mcp_server"
      ],
      "envFile": ".env"
    }
  }
}
```

#### Codex Client
```json
{
  "mcpServers": {
    "agentrag": {
      "command": "uv",
      "args": [
        "run",
        "python",
        "-m",
        "agentrag.mcp_server"
      ],
      "envFile": ".env"
    }
  }
}
```

#### KiloCode / Client Lain
```json
{
  "mcpServers": {
    "agentrag": {
      "transport": "stdio",
      "command": "uv",
      "args": [
        "run",
        "python",
        "-m",
        "agentrag.mcp_server"
      ],
      "envFile": ".env"
    }
  }
}
```

## Available Tools

### 1. query_memory
**Description:** Query the agentRAG memory system for relevant information

#### 🧠 Automatic Query Planning
Tool ini **otomatis mengklasifikasikan** query Anda tanpa perlu parameter manual:

**Auto-Detection Features:**
- **Intent Detection** - Mendeteksi tujuan query:
  - `explain_function` - Query tentang function/class/method
  - `bug_hunt` - Query tentang bug/error/exception
  - `refactor_guidance` - Query tentang refactoring
  - `find_snippet` - Query untuk contoh code
  - `general_query` - Query umum

- **Node Type Classification** - Otomatis membedakan:
  - `code` - Jika query menyebut "function", "class", "method", "code"
  - `text` - Jika query menyebut "docs", "documentation", "guide"

- **Language Detection** - Otomatis deteksi bahasa pemrograman:
  - "python function" → `language: python`
  - "javascript class" → `language: javascript`
  - "golang service" → `language: go`

- **Symbol Extraction** - Otomatis ekstrak nama function/class:
  - "function calculate_roi" → `symbol_name: calculate_roi`
  - "class UserService" → `symbol_name: UserService`

**Contoh Query Natural:**
```json
// Query: "python function untuk calculate ROI"
// Auto-detected:
//   - intent: explain_function
//   - node_type: code
//   - language: python
//   - symbol_name: calculate_roi

// Query: "bug in authentication error"
// Auto-detected:
//   - intent: bug_hunt
//   - node_type: null (search all)

// Query: "installation guide documentation"
// Auto-detected:
//   - intent: general_query
//   - node_type: text
```

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "query": {
      "type": "string",
      "description": "The query text to search for in the memory system"
    },
    "top_k": {
      "type": "integer",
      "description": "Number of results to return (default: 3)",
      "default": 3
    },
    "node_type": {
      "type": "string",
      "description": "Filter by node type: 'text' or 'code' (optional). Leave empty for auto-detection.",
      "enum": ["text", "code"]
    },
    "language": {
      "type": "string",
      "description": "Filter by programming language (e.g., 'python', 'javascript') (optional). Leave empty for auto-detection."
    },
    "access_level": {
      "type": "string",
      "description": "Filter by access level: 'public', 'internal', 'admin' (optional)",
      "default": "internal"
    }
  },
  "required": ["query"]
}
```

**Example Usage:**

**Natural Query (Recommended):**
```json
{
  "name": "query_memory",
  "arguments": {
    "query": "python function untuk calculate ROI"
  }
}
// Auto-detects: node_type=code, language=python, symbol_name=calculate_roi
```

**Manual Override (Optional):**
```json
{
  "name": "query_memory",
  "arguments": {
    "query": "function for upsert",
    "top_k": 5,
    "node_type": "code",
    "language": "python"
  }
}
```

### 2. ingest_documents
**Description:** Ingest documents into the agentRAG memory system

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "targets": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "description": "List of file paths, directories, or URLs to ingest"
    },
    "access_level": {
      "type": "string",
      "description": "Access level for the ingested documents",
      "default": "internal",
      "enum": ["public", "internal", "admin"]
    },
    "dry_run": {
      "type": "boolean",
      "description": "Preview what would be ingested without actually writing to the database",
      "default": false
    }
  },
  "required": ["targets"]
}
```

**Example Usage:**
```json
{
  "name": "ingest_documents",
  "arguments": {
    "targets": ["/path/to/docs", "https://example.com/docs"],
    "access_level": "internal",
    "dry_run": true
  }
}
```

### 3. health_check
**Description:** Check the health of the agentRAG system

**Input Schema:**
```json
{
  "type": "object",
  "properties": {},
  "required": []
}
```

**Example Usage:**
```json
{
  "name": "health_check",
  "arguments": {}
}
```

---

## 🔄 Query Flow & Fallback Strategy

### Search Flow
```
User Query
    ↓
Automatic Query Planning
  - Detect intent (explain_function, bug_hunt, etc.)
  - Classify node_type (code/text)
  - Extract language (python, javascript, etc.)
  - Extract symbol_name (function/class name)
    ↓
Strict Search (with all filters)
    ↓
Results found? → Return ranked results
    ↓
No results? → Fallback Strategy
    ↓
Fallback 1: Remove symbol_name filter
Fallback 2: Remove language filter
Fallback 3: Remove node_type filter
    ↓
Return best available results
```

### Fallback Example
```json
// Query: "python function calculate_roi"
// 
// Strict search:
//   node_type=code, language=python, symbol_name=calculate_roi
//   → No results
//
// Fallback 1:
//   node_type=code, language=python (remove symbol_name)
//   → Found 3 results ✓
```

---

## Usage Examples

### 1. Natural Language Queries (Recommended)

**Find Python Function:**
```json
{
  "name": "query_memory",
  "arguments": {
    "query": "python function untuk calculate ROI"
  }
}
// Auto-detects: code, python, calculate_roi
```

**Find Bug/Error:**
```json
{
  "name": "query_memory",
  "arguments": {
    "query": "bug in authentication error"
  }
}
// Auto-detects: intent=bug_hunt, searches all types
```

**Find Documentation:**
```json
{
  "name": "query_memory",
  "arguments": {
    "query": "installation guide documentation"
  }
}
// Auto-detects: node_type=text
```

**Find Code Example:**
```json
{
  "name": "query_memory",
  "arguments": {
    "query": "show javascript class for user authentication"
  }
}
// Auto-detects: code, javascript, UserAuthentication
```

### 2. Manual Override (When Needed)

**Force Specific Language:**
```json
{
  "name": "query_memory",
  "arguments": {
    "query": "calculate ROI",
    "node_type": "code",
    "language": "python",
    "top_k": 5
  }
}
```

**Search Only Documentation:**
```json
{
  "name": "query_memory",
  "arguments": {
    "query": "API endpoints",
    "node_type": "text",
    "top_k": 10
  }
}
```

### 3. Ingesting Documents
  }
}
```

### Querying Documentation
```json
{
  "name": "query_memory",
  "arguments": {
    "query": "installation guide",
    "node_type": "text",
    "access_level": "public"
  }
}
```

### Ingesting Documents
```json
{
  "name": "ingest_documents",
  "arguments": {
    "targets": ["/docs", "https://example.com/api-docs"],
    "access_level": "internal"
  }
}
```

## Response Format

### Query Response
```json
{
  "query": "test query",
  "total_hits": 3,
  "fallback_used": false,
  "final_top_k": 3,
  "hits": [
    {
      "rank": 1,
      "source_id": "file.py",
      "hierarchy_path": "file.py > calculate_roi",
      "content": "def calculate_roi(gain, cost):",
      "node_type": "code",
      "score": 0.95,
      "language": "python",
      "symbol_name": "calculate_roi"
    }
  ]
}
```

### Ingest Response
```json
{
  "nodes_created": 5,
  "skipped": 0,
  "new_chunks": 5,
  "unchanged_chunks": 0,
  "stale_deleted": 0,
  "dry_run": false
}
```

### Health Check Response
```json
{
  "ok": true,
  "qdrant_ok": true,
  "embedder_ok": true,
  "collection_exists": true,
  "collection_points": 1234,
  "collection_name": "agentrag_memory",
  "embedding_provider": "fastembed",
  "embedding_dimensions": 768
}
```

## Error Handling

### Common Errors

1. **Qdrant Connection Failed**
```json
{
  "ok": false,
  "error": {
    "code": "QDRANT_PREFLIGHT_FAILED",
    "message": "URL is not reachable within 2.0s at http://localhost:6333. error=Connection refused",
    "details": {
      "collection": "agentrag_memory"
    }
  }
}
```

2. **Embedding Model Failed**
```json
{
  "ok": false,
  "error": {
    "code": "EMBEDDING_PREFLIGHT_FAILED",
    "message": "Failed to initialize fastembed model 'jinaai/jina-embeddings-v2-base-code': ...",
    "details": {
      "provider": "fastembed",
      "model": "jinaai/jina-embeddings-v2-base-code"
    }
  }
}
```

3. **Dimension Mismatch**
```json
{
  "ok": false,
  "error": {
    "code": "DIMENSION_PREFLIGHT_FAILED",
    "message": "embedding dimension mismatch: model_dim=768 collection_dim=4096 collection='agentrag_memory'. Use a new collection or recreate this collection and re-ingest.",
    "details": {
      "collection": "agentrag_memory",
      "embed_dimensions": 768
    }
  }
}
```

## Troubleshooting

### Common Issues

1. **MCP Server Not Starting**
   - Check if Python 3.10+ is installed
   - Verify all dependencies are installed
   - Check environment variables in `.env` file

2. **Tools Not Available**
   - Ensure MCP client is properly configured
   - Check server logs for errors
   - Verify network connectivity to Qdrant

3. **Query Returns No Results**
   - Check if documents have been ingested
   - Verify collection exists in Qdrant
   - Check embedding dimensions match

### Debug Mode
To enable debug logging, set environment variable:
```bash
export LOG_LEVEL=DEBUG
```

## Performance Considerations

- **Memory Usage:** MCP Server runs efficiently with minimal memory footprint
- **Latency:** Query response time depends on Qdrant performance and network latency
- **Batch Processing:** Large batch operations may take time depending on document size

## Security

- **API Keys:** Store Qdrant API keys in `.env` file, never hardcode
- **Access Control:** Use `access_level` parameter to control document visibility
- **Network:** Ensure secure connection to Qdrant Cloud

## Support

For issues and questions:
1. Check logs for error details
2. Verify configuration settings
3. Test with simple queries first
4. Ensure all dependencies are up to date

## Additional Resources

- [Vector Dimensions Explained](docs/VECTOR_DIMENSIONS.md) - Understanding embedding dimensions and troubleshooting dimension mismatch errors
- [MCP Testing Guide](MCP_TESTING.md) - Comprehensive testing documentation
- [MCP Quick Reference](MCP_QUICK_REF.md) - Quick reference for tools and parameters
- [Main README](README.md) - Project overview and features