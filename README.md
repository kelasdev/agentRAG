# agentRAG

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP Compatible](https://img.shields.io/badge/MCP-compatible-purple.svg)](https://modelcontextprotocol.io/)

> **Intelligent Memory System for AI Agents** - Hybrid text+code RAG that helps agents reason over codebases with structured retrieval instead of naive grep-and-guess.

## 🎯 Overview

**agentRAG** adalah sistem memory cerdas yang dirancang khusus untuk AI agents. Sistem ini membantu agent bekerja di atas codebase dan dokumentasi dengan retrieval yang lebih terstruktur, sehingga agent tidak hanya membuka file secara acak atau menebak arsitektur dari potongan teks yang kebetulan cocok.

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

- **👀 Watch Mode** - Pantau folder dan ingest perubahan secara batch:
  - Command: `agentrag watch <folder>`
  - Menghormati `.gitignore`
  - Debounce, batching, dan extension filter

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

If you want to use `EMBEDDING_PROVIDER=llama_cpp_python` on Windows/Python 3.12, do not rely on a plain `pip install llama-cpp-python`. Use the verified wheel install:

```bash
pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu --only-binary=:all:
python -c "from llama_cpp import Llama; print('Success: llama-cpp-python is working!')"
```

For a repeatable Windows setup, you can also run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install_windows.ps1
```

For development/testing:

```bash
pip install -r requirements-dev.txt
```

### Quick Start

3. Run ingest (local file/dir):

```bash
agentrag ingest docs/PRD.md
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

Watch a folder and auto-ingest changes:

```bash
agentrag watch ./docs
agentrag watch ./my-project --extensions .py,.md --batch-size 3 --debounce-seconds 2
agentrag watch ./my-project --dry-run
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
- [MCP_SERVER_README.md](docs/MCP_SERVER_README.md) - Complete MCP server guide
- [MCP_QUICK_REF.md](docs/MCP_QUICK_REF.md) - Quick reference
- [MCP_TESTING.md](docs/MCP_TESTING.md) - Testing guide
- [MCP_INSPECTOR_GUIDE.md](docs/MCP_INSPECTOR_GUIDE.md) - Visual testing with MCP Inspector

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
 - `watch` monitors file changes and triggers batched `ingest` calls.
 - `watch` uses Git-aware ignore handling when the target folder is inside a Git repo.
 - `watch` supports `--dry-run`, `--extensions`, `--batch-size`, `--debounce-seconds`, and `--non-recursive`.

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

### .gitignore Support

When ingesting directories, agentRAG automatically respects `.gitignore` patterns:

- Reads `.gitignore` from the target directory
- Excludes files matching patterns (wildcards, directories)
- Always excludes `.git/` directory by default
- Works with nested directories and complex patterns

Example:
```bash
# .gitignore in your project
*.pyc
__pycache__/
node_modules/
dist/

# Ingest will automatically skip these files
agentrag ingest ./my-project
```

### Code Graph (Definitions / Callers / Callees)

agentRAG sekarang mendukung navigasi graph sederhana berbasis payload index **di Qdrant** (tanpa penyimpanan lain):

- **Definitions**: temukan chunk definisi simbol (function/class/method) via `code_metadata.symbol_name`.
- **Callers**: temukan chunk yang memanggil sebuah simbol via `code_metadata.calls`.
- **Callees**: ambil daftar pemanggilan dari payload definisi (field `code_metadata.calls`).

CLI commands:

```bash
# Watch local changes and auto-ingest
agentrag watch ./my-project --extensions .py,.md

# Definisi simbol
agentrag defs calculate_roi --language python --limit 10

# Siapa yang memanggil simbol ini?
agentrag callers calculate_roi --language python --limit 25

# Simbol ini memanggil apa saja?
agentrag callees calculate_roi --language python
```

MCP tool (opsional): `code_graph` dengan `action` salah satu dari: `definitions`, `callers`, `callees`.

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

### Quick Test

Run all tests:

```bash
./scripts/run_all_tests.sh
```

Or run individual test suites:

```bash
# Unit tests (pytest)
pytest -q

# Integration tests
python scripts/test_mcp_integration.py

# Scenario tests
python scripts/test_scenarios.py
```

### Test Coverage

**Current Status:** ✅ 54/56 tests passing (96.4% success rate)

- **Unit Tests:** 36 passed, 2 skipped
- **Integration Tests:** 3 passed
- **Scenario Tests:** 15 passed

See [TEST_REPORT.md](docs/TEST_REPORT.md) for detailed test results and coverage analysis.

### MCP Server Testing

Test the MCP server integration:

```bash
# Unit tests
pytest tests/test_mcp_server.py -v

# Integration test
python scripts/test_mcp_integration.py

# Visual testing with MCP Inspector
npx @modelcontextprotocol/inspector python -m agentrag.mcp_server
```

See [MCP_TESTING.md](docs/MCP_TESTING.md) for comprehensive testing guide and [MCP_QUICK_REF.md](docs/MCP_QUICK_REF.md) for quick reference.

---

## 📚 Documentation

- [Vector Dimensions Explained](docs/VECTOR_DIMENSIONS.md) - Memahami dimensi vektor dan embedding models
- [MCP Server Guide](docs/MCP_SERVER_README.md) - Complete MCP server documentation
- [MCP Quick Reference](docs/MCP_QUICK_REF.md) - Quick reference for MCP tools
- [MCP Testing Guide](docs/MCP_TESTING.md) - Comprehensive testing guide
- [MCP Inspector Guide](docs/MCP_INSPECTOR_GUIDE.md) - Visual testing with MCP Inspector

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
