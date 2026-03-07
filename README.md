# agentRAG

Foundation implementation for hybrid text+code ingest to Qdrant Cloud.

## Quickstart

1. Copy `.env.example` to `.env` and fill `QDRANT_URL` + `QDRANT_API_KEY`.
2. Install dependencies with `uv sync` (recommended) or `pip install -e .`.
3. Run ingest:

```bash
agentrag ingest PRD.md
```

4. Run query:

```bash
agentrag query "qdrant cloud url" --node-type text --top-k 3
```

5. Show extracted plan (intent + constraints):

```bash
agentrag query "show python function for qdrant upsert" --show-plan
```

6. Check Qdrant connectivity:

```bash
agentrag health
```

## Ingest Behavior

- Re-ingest uses delta sync per `source_id`.
- Chunk identity is stable: `hash(source_id + content_hash)`.
- Only changed/new chunks are upserted.
- Stale chunks (no longer present in source) are deleted.
- Dry-run is available to inspect changes without writing:

```bash
agentrag ingest ../PYRAG/test_data --dry-run
```

## Code Chunking

- Python uses built-in `ast` extraction.
- JavaScript/TypeScript/Go/Java use `tree-sitter` for structural chunk extraction.
- If `tree-sitter` runtime is unavailable at execution time, the chunker falls back to a regex-based structural parser for those languages.

## Testing

Install dev dependencies:

```bash
pip install -e ".[dev]"
```

Run tests:

```bash
pytest -q
```
