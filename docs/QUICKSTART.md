# agentRAG - Quick Start Guide

## Prerequisites

- Python 3.10+
- Qdrant Cloud instance (atau self-hosted)
- 2GB RAM minimum
- 2 CPU cores minimum

## Installation

### Option 1: Using uv (Recommended)
```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone repository
git clone <your-repo-url>
cd agentRAG

# Install dependencies
uv sync
```

### Option 2: Using pip
```bash
# Clone repository
git clone <your-repo-url>
cd agentRAG

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
pip install -e .
```

## Configuration

1. Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

2. Edit `.env` dengan konfigurasi Anda:
```env
# Qdrant Configuration (REQUIRED)
QDRANT_URL=https://your-qdrant-instance.com
QDRANT_API_KEY=your_api_key_here

# Embedding Provider (REQUIRED)
EMBEDDING_PROVIDER=fastembed
EMBEDDING_MODEL=jinaai/jina-embeddings-v2-base-code

# Optional: Retrieval settings
FINAL_TOP_K=3
DEFAULT_TOP_K_MEMORY_QUERY=3

# Optional: Web ingest
JINA_READER_BASE_URL=https://r.jina.ai/
WEB_FETCH_TIMEOUT_SECONDS=45
```

## Verify Installation

```bash
# Check health
agentrag health

# Expected output:
# {
#   "ok": true,
#   "qdrant_connected": true,
#   "embedding_provider": "fastembed",
#   "dimensions": 768
# }
```

## Basic Usage

### 1. Ingest Local Files

```bash
# Single file
agentrag ingest README.md

# Multiple files
agentrag ingest file1.md file2.py

# Directory (recursive)
agentrag ingest ./docs

# Dry-run (preview changes)
agentrag ingest ./docs --dry-run
```

### 2. Ingest from URLs

```bash
# Single URL
agentrag ingest "https://example.com/guide.pdf"

# Multiple URLs
agentrag ingest \
  "https://example.com/doc1.md" \
  "https://example.com/doc2.pdf"

# Mixed local + URL
agentrag ingest ./docs "https://example.com/spec"
```

### 3. Watch Local Changes

```bash
# Watch a folder and auto-ingest changes
agentrag watch ./docs

# Only watch selected file types
agentrag watch ./docs --extensions .py,.md

# Test watcher without ingesting
agentrag watch ./docs --dry-run
```

### 4. Query

```bash
# Basic query
agentrag query "how to install"

# Filter by type
agentrag query "authentication" --node-type text

# Limit results
agentrag query "calculate function" --top-k 5

# Code-specific query
agentrag query "find calculate_roi function" --node-type code
```

## Output Format

All commands return JSON:

### Ingest Success
```json
{
  "ok": true,
  "new_chunks": 15,
  "unchanged_chunks": 5,
  "stale_deleted": 2,
  "skipped": 0,
  "elapsed_seconds": 3.45
}
```

### Query Success
```json
{
  "ok": true,
  "plan": {
    "intent": "find_snippet",
    "node_type": "code",
    "language": "python",
    "symbol_name": "calculate_roi"
  },
  "hits": [
    {
      "id": "uuid-here",
      "score": 0.95,
      "payload": {
        "node_type": "code",
        "content": "def calculate_roi(gain, cost):\n    ...",
        "source_id": "finance/metrics.py",
        "code_metadata": {
          "language": "python",
          "symbol_name": "calculate_roi"
        }
      }
    }
  ]
}
```

### Error Response
```json
{
  "ok": false,
  "error": {
    "code": "QDRANT_PREFLIGHT_FAILED",
    "message": "Failed to connect to Qdrant",
    "details": {
      "url": "https://your-qdrant-instance.com"
    }
  }
}
```

## Advanced Usage

### Delta Sync (Re-ingest)

agentRAG automatically handles delta sync:

```bash
# First ingest
agentrag ingest ./docs
# Output: new_chunks=100, unchanged_chunks=0

# Modify some files, then re-ingest
agentrag ingest ./docs
# Output: new_chunks=5, unchanged_chunks=95, stale_deleted=3
```

### Embedding Providers

#### FastEmbed (Default - Local)
```env
EMBEDDING_PROVIDER=fastembed
EMBEDDING_MODEL=jinaai/jina-embeddings-v2-base-code
```

#### Llama.cpp (Local GGUF)
```env
EMBEDDING_PROVIDER=llama_cpp_python
LLAMA_CPP_EMBED_MODEL_PATH=./models/nomic-embed-text-v2-moe.Q4_K_M.gguf
LLAMA_CPP_N_THREADS=4
```

#### OpenAI-Compatible API
```env
EMBEDDING_PROVIDER=openai_compatible
EMBEDDING_MODEL=text-embedding-3-small
OPENAI_COMPATIBLE_BASE_URL=https://api.openai.com/v1
OPENAI_COMPATIBLE_API_KEY=sk-...
```

## Integration Examples

### Python Module

```python
from agentrag.config import get_settings
from agentrag.providers.embeddings import EmbeddingProvider
from agentrag.qdrant_store import QdrantStore
from agentrag.ingest import ingest_targets

# Initialize
settings = get_settings()
embedder = EmbeddingProvider(
    provider=settings.embedding_provider,
    model_name=settings.embedding_model,
    # ... other params
)
store = QdrantStore(
    url=settings.qdrant_url,
    api_key=settings.qdrant_api_key,
    collection_name=settings.collection_name,
    vector_size=embedder.dimensions
)

# Ingest
result = ingest_targets(
    targets=["./docs"],
    store=store,
    embedder=embedder,
    dry_run=False
)
print(f"Ingested: {result['new_chunks']} new chunks")

# Query
from agentrag.pipeline import query_pipeline
hits = query_pipeline(
    query_text="how to install",
    store=store,
    embedder=embedder,
    top_k=3
)
```

### MCP Server (AI Agents)

See `MCP_SERVER_README.md` for integration with Claude, Kiro, etc.

## Troubleshooting

### Connection Failed
```bash
# Test Qdrant connectivity
curl -X GET "$QDRANT_URL/collections" \
  -H "api-key: $QDRANT_API_KEY"
```

### Dimension Mismatch
```
Error: embedding dimension mismatch: model_dim=768 collection_dim=4096
```

**Solution:** Delete collection and re-ingest, or use different collection name.

### Slow Ingest
- Use `--dry-run` to estimate time
- Ingest in smaller batches
- Check network latency to Qdrant

### Empty Query Results
- Check if data is ingested: `agentrag health`
- Try broader query terms
- Remove `--node-type` filter
- Increase `--top-k`

## Best Practices

1. **Always dry-run first** for large ingests
2. **Use delta sync** - re-ingest same sources for updates
3. **Monitor Qdrant** - check storage usage
4. **Test queries** - verify retrieval quality
5. **Backup .env** - keep credentials secure
6. **Version control** - exclude `.env` from git

## Next Steps

- Read `CORE_READINESS.md` for production deployment
- Check `PRD.md` for architecture details
- See `tests/` for usage examples
- Join community for support

## Support

- GitHub Issues: <your-repo-url>/issues
- Documentation: See README.md
- Examples: See `tests/` directory
