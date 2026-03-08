# agentRAG

> **Intelligent Memory System for AI Agents** - Hybrid text+code RAG with automatic query understanding and MCP integration.

## 🎯 Overview

**agentRAG** adalah sistem memory cerdas yang dirancang khusus untuk AI agents. Sistem ini memahami konteks query Anda secara otomatis, membedakan antara dokumentasi dan kode, serta memberikan hasil pencarian yang relevan dengan ranking yang akurat.

### ✨ Key Features

- **🧠 Automatic Query Planning** - Sistem otomatis mengklasifikasikan query Anda:
  - Deteksi intent (explain function, bug hunt, refactor, dll)
  - Klasifikasi tipe konten (code vs documentation)
  - Ekstraksi bahasa pemrograman
  - Identifikasi nama function/class yang dicari

- **🔄 Smart Fallback Strategy** - Jika pencarian strict tidak menemukan hasil, sistem secara bertahap melonggarkan filter untuk memberikan hasil terbaik yang tersedia

- **📦 Hybrid Chunking** - Strategi chunking yang berbeda untuk setiap tipe konten:
  - **Code**: AST-based chunking (per function/class) menggunakan Tree-sitter
  - **Text**: Delimiter-based chunking (per section/topic) untuk menjaga konteks

- **🔌 MCP Server Integration** - Native support untuk Model Context Protocol:
  - 3 tools siap pakai: `query_memory`, `ingest_documents`, `health_check`
  - Compatible dengan Claude, Kiro CLI, dan MCP clients lainnya
  - Natural language query support

- **⚡ Delta Sync** - Re-ingest yang efisien:
  - Hanya update chunks yang berubah
  - Hapus chunks yang sudah tidak ada
  - Stable chunk identity dengan content hashing

- **🌐 URL Ingest** - Ingest langsung dari web:
  - Support PDF, DOCX, Markdown, HTML
  - Auto-sanitization untuk menghilangkan noise (header/footer/menu)
  - Via Jina Reader API

- **🎨 Multi-Language Support** - Python, JavaScript, TypeScript, Go, Java, Rust, C/C++

### 🏗️ Architecture

```
User Query → Query Planner → Retrieval → Ranking → Results
                ↓
         Auto-detect:
         - Intent
         - Node Type
         - Language
         - Symbol Name
```

### 🚀 Use Cases

- **AI Agent Memory** - Berikan AI agent akses ke codebase dan dokumentasi Anda
- **Code Search** - Cari function, class, atau pattern tertentu dalam codebase
- **Documentation Search** - Temukan guide, tutorial, atau API docs dengan cepat
- **Bug Investigation** - Cari error patterns atau exception handling
- **Refactoring Assistant** - Temukan code yang perlu di-refactor

---

## 📦 Installation

### Prerequisites
- Python 3.10+
- Qdrant Cloud account (atau local Qdrant instance)
- Understanding of [vector dimensions](docs/VECTOR_DIMENSIONS.md) (recommended)

### Install

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

### Quick Start

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

---

## 🔌 MCP Server Integration

agentRAG menyediakan MCP (Model Context Protocol) server untuk integrasi dengan AI agents.

### Available Tools

1. **query_memory** - Search dengan automatic query planning
2. **ingest_documents** - Tambah dokumen ke memory
3. **health_check** - Cek status sistem

### Configuration

Add to your MCP client config (e.g., Kiro CLI `~/.kiro/mcp.json`):

```json
{
  "mcpServers": {
    "agentrag": {
      "command": "python",
      "args": ["-m", "agentrag.mcp_server"],
      "cwd": "/path/to/agentRAG",
      "env": {
        "PYTHONPATH": "/path/to/agentRAG"
      }
    }
  }
}
```

### Usage Example

```
AI Agent: "Use agentrag to find python function for calculate ROI"

agentRAG automatically:
- Detects: intent=explain_function, node_type=code, language=python
- Searches with filters
- Returns ranked results
```

**Documentation:**
- [MCP_SERVER_README.md](MCP_SERVER_README.md) - Complete MCP server guide
- [MCP_QUICK_REF.md](MCP_QUICK_REF.md) - Quick reference
- [MCP_TESTING.md](MCP_TESTING.md) - Testing guide

---

## 📚 Features Deep Dive

### Automatic Query Planning

Query Anda otomatis dianalisis untuk mendeteksi:

**Intent Detection:**
- `explain_function` - "python function calculate_roi"
- `bug_hunt` - "bug in authentication error"
- `refactor_guidance` - "refactor user service"
- `find_snippet` - "show code example"
- `general_query` - Query umum

**Node Type Classification:**
- `code` - Jika menyebut "function", "class", "method"
- `text` - Jika menyebut "docs", "documentation", "guide"

**Language Detection:**
- Auto-detect dari keyword: "python", "javascript", "golang", dll

**Symbol Extraction:**
- "function calculate_roi" → `symbol_name: calculate_roi`
- "class UserService" → `symbol_name: UserService`

### Smart Fallback Strategy

Jika strict search tidak menemukan hasil:

```
Strict Search (all filters)
    ↓ No results?
Fallback 1: Remove symbol_name
    ↓ No results?
Fallback 2: Remove language
    ↓ No results?
Fallback 3: Remove node_type
    ↓
Return best available results
```

### Hybrid Chunking Strategy

| Source Type | Strategy | Description |
| --- | --- | --- |
| Code | AST-Based | Per function/class menggunakan Tree-sitter atau Python AST |
| Text | Delimiter-Based | Per section/topic berdasarkan Markdown headers |

**Supported Languages:**
- Python (built-in AST)
- JavaScript/TypeScript (Tree-sitter)
- Go, Java, Rust, C/C++ (Tree-sitter)

**Learn More:**
- [Vector Dimensions Explained](docs/VECTOR_DIMENSIONS.md) - Memahami dimensi vektor dan embedding models

---

## 🔧 Advanced Usage

### Ingest Behavior

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

### URL Ingest Details

- Fetch path: `JINA_READER_BASE_URL + target_url` (default `https://r.jina.ai/`).
- Intended web document targets: `md`, `txt`, `rst`, `pdf`, `docx`, `doc`, `html`, `htm`, and generic web pages.
- Sanitization removes common navigation/header/footer fragments, separator lines, and emoji-heavy noise before chunking.
- If fetch fails or sanitized content is empty, target is counted as `skipped`.

### URL Ingest Config

Set in `.env`:

```env
JINA_READER_BASE_URL=https://r.jina.ai/
WEB_FETCH_TIMEOUT_SECONDS=45
```

- `JINA_READER_BASE_URL`: Base endpoint for web-to-text extraction.
- `WEB_FETCH_TIMEOUT_SECONDS`: Request timeout per URL fetch.

---

## 📋 Chunking Strategy

| Source Type | Strategy | Description |
| --- | --- | --- |
| Kode Pemrograman | AST-Based Chunking | Menggunakan parser (seperti Tree-sitter) untuk memotong kode berdasarkan struktur logika (Abstract Syntax Tree), seperti per class atau per fungsi. Tujuannya agar sintaks tetap utuh dan tidak terpotong di tengah blok logika. |
| Teks / Narasi | Safeword / Delimiter | Memotong teks berdasarkan penanda batas (misalnya `===BATAS===` atau header Markdown `#`, `##`). Tujuannya menjaga satu gagasan/topik tetap berada dalam satu chunk utuh tanpa merusak makna paragraf. |

- Python uses built-in `ast` extraction.
- JavaScript/TypeScript/Go/Java use `tree-sitter` for structural chunk extraction.
- If `tree-sitter` runtime is unavailable at execution time, the chunker falls back to a regex-based structural parser for those languages.

---

## 🧪 Testing

Install dev dependencies:

```bash
pip install -r requirements-dev.txt
```

Run tests:

```bash
pytest -q
```

### MCP Server Testing

Test the MCP server integration:

```bash
# Unit tests
pytest tests/test_mcp_server.py -v

# Integration test
python scripts/test_mcp_integration.py
```

See [MCP_TESTING.md](MCP_TESTING.md) for comprehensive testing guide and [MCP_QUICK_REF.md](MCP_QUICK_REF.md) for quick reference.

---

## 📚 Documentation

- [Vector Dimensions Explained](docs/VECTOR_DIMENSIONS.md) - Memahami dimensi vektor dan embedding models
- [MCP Server Guide](MCP_SERVER_README.md) - Complete MCP server documentation
- [MCP Quick Reference](MCP_QUICK_REF.md) - Quick reference for MCP tools
- [MCP Testing Guide](MCP_TESTING.md) - Comprehensive testing guide

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

- [Qdrant](https://qdrant.tech/) - Vector database
- [FastEmbed](https://github.com/qdrant/fastembed) - Fast embedding models
- [Tree-sitter](https://tree-sitter.github.io/) - Code parsing
- [Model Context Protocol](https://modelcontextprotocol.io/) - AI agent integration
