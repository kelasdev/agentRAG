# agentRAG

Foundation implementation for hybrid text+code ingest to Qdrant Cloud.

## Quickstart

1. Copy `.env.example` to `.env` and fill `QDRANT_URL` + `QDRANT_API_KEY`.
2. Install dependencies with `uv sync` (recommended) or:

```bash
pip install -r requirements.txt
pip install -e .
```

For development/testing:

```bash
pip install -r requirements-dev.txt
```
3. Run ingest (local file/dir):

```bash
agentrag ingest PRD.md
```

Ingest from web URL (via Jina Reader public API):

```bash
agentrag ingest "https://example.com/guide.pdf"
```

Ingest multiple URLs:

```bash
agentrag ingest \
  "https://example.com/a.pdf" \
  "https://example.com/b.md" \
  "https://example.com/c.docx"
```

Mixed local + URL targets:

```bash
agentrag ingest ./docs "https://example.com/spec"
```

4. Run query:

```bash
agentrag query "qdrant cloud url" --node-type text --top-k 3
```

5. Query result is returned as JSON (MCP-friendly), including detected plan and hits.

6. Check Qdrant connectivity:

```bash
agentrag health
```

## Ingest Behavior

- Re-ingest uses delta sync per `source_id`.
- Chunk identity is stable: `hash(source_id + content_hash)`.
- Only changed/new chunks are upserted.
- Stale chunks (no longer present in source) are deleted.
- `ingest` accepts local files/directories and `http(s)` URLs in the same command.
- URL ingest fetches content through `https://r.jina.ai/` and sanitizes common web noise (header/footer/menu separators/emojis) before chunking.
- For URL sources, `source_id` is the URL itself. Re-running ingest on the same URL performs delta sync against that URL.
- Dry-run is available to inspect changes without writing:

```bash
agentrag ingest ../PYRAG/test_data --dry-run
```

Dry-run with multiple URLs:

```bash
agentrag ingest \
  "https://example.com/a.pdf" \
  "https://example.com/b" \
  --dry-run
```

## URL Ingest Details

- Fetch path: `JINA_READER_BASE_URL + target_url` (default `https://r.jina.ai/`).
- Intended web document targets: `md`, `txt`, `rst`, `pdf`, `docx`, `doc`, `html`, `htm`, and generic web pages.
- Sanitization removes common navigation/header/footer fragments, separator lines, and emoji-heavy noise before chunking.
- If fetch fails or sanitized content is empty, target is counted as `skipped`.

## URL Ingest Config

Set in `.env`:

```env
JINA_READER_BASE_URL=https://r.jina.ai/
WEB_FETCH_TIMEOUT_SECONDS=45
```

- `JINA_READER_BASE_URL`: Base endpoint for web-to-text extraction.
- `WEB_FETCH_TIMEOUT_SECONDS`: Request timeout per URL fetch.

## Chunking Strategy

| Source Type | Strategy | Description |
| --- | --- | --- |
| Kode Pemrograman | AST-Based Chunking | Menggunakan parser (seperti Tree-sitter) untuk memotong kode berdasarkan struktur logika (Abstract Syntax Tree), seperti per class atau per fungsi. Tujuannya agar sintaks tetap utuh dan tidak terpotong di tengah blok logika. |
| Teks / Narasi | Safeword / Delimiter | Memotong teks berdasarkan penanda batas (misalnya `===BATAS===` atau header Markdown `#`, `##`). Tujuannya menjaga satu gagasan/topik tetap berada dalam satu chunk utuh tanpa merusak makna paragraf. |

- Python uses built-in `ast` extraction.
- JavaScript/TypeScript/Go/Java use `tree-sitter` for structural chunk extraction.
- If `tree-sitter` runtime is unavailable at execution time, the chunker falls back to a regex-based structural parser for those languages.

## Testing

Install dev dependencies:

```bash
pip install -r requirements-dev.txt
```

Run tests:

```bash
pytest -q
```
