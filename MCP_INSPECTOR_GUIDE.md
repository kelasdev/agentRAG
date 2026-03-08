# Testing agentRAG with MCP Inspector

## 🎯 Overview

MCP Inspector adalah tool visual untuk testing MCP servers secara interaktif. Anda bisa melihat tools yang tersedia, test dengan parameter custom, dan lihat request/response JSON secara real-time.

---

## 📦 Installation

### 1. Install MCP Inspector (via npm)

```bash
npm install -g @modelcontextprotocol/inspector
```

Atau dengan npx (tanpa install global):
```bash
npx @modelcontextprotocol/inspector
```

---

## 🚀 Quick Start

### Method 1: Direct Command (Recommended)

```bash
cd /home/kelasdev/agentRAG
npx @modelcontextprotocol/inspector python -m agentrag.mcp_server
```

Ini akan:
1. Start MCP server
2. Open browser ke `http://localhost:5173`
3. Connect inspector ke server

### Method 2: Separate Terminal

**Terminal 1 - Start MCP Server:**
```bash
cd /home/kelasdev/agentRAG
source .venv/bin/activate
python -m agentrag.mcp_server
```

**Terminal 2 - Start Inspector:**
```bash
npx @modelcontextprotocol/inspector
```

---

## 🧪 Testing Workflow

### Step 1: Open Inspector

Browser akan terbuka otomatis di `http://localhost:5173`

### Step 2: View Available Tools

Di sidebar kiri, Anda akan melihat 3 tools:
- ✅ `query_memory`
- ✅ `ingest_documents`
- ✅ `health_check`

### Step 3: Test Each Tool

---

## 📋 Test Scenarios

### 1. Health Check (Paling Mudah)

**Click:** `health_check` tool

**Parameters:** (kosong)

**Expected Response:**
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

**✅ Success Indicators:**
- `ok: true`
- `qdrant_ok: true`
- `embedder_ok: true`

---

### 2. Query Memory (Natural Language)

**Click:** `query_memory` tool

**Test Case 1: Find Python Function**
```json
{
  "query": "python function untuk calculate ROI"
}
```

**Expected Response:**
```json
{
  "query": "python function untuk calculate ROI",
  "total_hits": 3,
  "fallback_used": false,
  "final_top_k": 3,
  "hits": [
    {
      "rank": 0.8234,
      "source_id": "/path/to/file.py",
      "content": "def calculate_roi(...):",
      "node_type": "code",
      "language": "python",
      "symbol_name": "calculate_roi"
    }
  ]
}
```

**Test Case 2: Find Documentation**
```json
{
  "query": "installation guide documentation"
}
```

**Test Case 3: Bug Hunting**
```json
{
  "query": "bug in authentication error"
}
```

**Test Case 4: Manual Override**
```json
{
  "query": "calculate",
  "node_type": "code",
  "language": "python",
  "top_k": 5
}
```

---

### 3. Ingest Documents (Dry Run)

**Click:** `ingest_documents` tool

**Test Case 1: Local File (Dry Run)**
```json
{
  "targets": ["/home/kelasdev/agentRAG/test_data/README.md"],
  "access_level": "internal",
  "dry_run": true
}
```

**Expected Response:**
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

**Test Case 2: URL (Dry Run)**
```json
{
  "targets": ["https://example.com/docs"],
  "dry_run": true
}
```

**Test Case 3: Multiple Targets**
```json
{
  "targets": [
    "/home/kelasdev/agentRAG/README.md",
    "https://example.com/guide"
  ],
  "access_level": "public",
  "dry_run": true
}
```

---

## 🔍 Inspector Features

### 1. Request/Response View

Inspector menampilkan:
- **Request JSON** - Parameter yang dikirim
- **Response JSON** - Hasil dari server
- **Timing** - Berapa lama request diproses

### 2. Tool Schema View

Klik tool untuk melihat:
- **Input Schema** - Parameter yang tersedia
- **Required Fields** - Parameter wajib
- **Optional Fields** - Parameter opsional
- **Enums** - Nilai yang diperbolehkan

### 3. History

Inspector menyimpan history request:
- Lihat request sebelumnya
- Re-run dengan parameter yang sama
- Compare responses

---

## 🎨 Visual Guide

```
┌─────────────────────────────────────────────────────────────┐
│ MCP Inspector                                    [x]        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Sidebar (Left)          │  Main Panel (Right)              │
│  ─────────────────       │  ──────────────────              │
│                          │                                   │
│  📋 Tools:               │  Tool: query_memory               │
│    ✓ query_memory        │                                   │
│    ✓ ingest_documents    │  Parameters:                      │
│    ✓ health_check        │  ┌─────────────────────────────┐ │
│                          │  │ {                           │ │
│  📊 History:             │  │   "query": "python func"    │ │
│    • Request #1          │  │ }                           │ │
│    • Request #2          │  └─────────────────────────────┘ │
│    • Request #3          │                                   │
│                          │  [Execute] [Clear]                │
│                          │                                   │
│                          │  Response:                        │
│                          │  ┌─────────────────────────────┐ │
│                          │  │ {                           │ │
│                          │  │   "total_hits": 3,          │ │
│                          │  │   "hits": [...]             │ │
│                          │  │ }                           │ │
│                          │  └─────────────────────────────┘ │
│                          │                                   │
└─────────────────────────────────────────────────────────────┘
```

---

## 🐛 Troubleshooting

### Issue 1: Inspector Can't Connect

**Error:** "Failed to connect to MCP server"

**Solution:**
```bash
# Check if server is running
ps aux | grep mcp_server

# Check if port is available
lsof -i :5173

# Restart with verbose logging
python -m agentrag.mcp_server --verbose
```

### Issue 2: Tools Not Showing

**Error:** No tools visible in sidebar

**Solution:**
```bash
# Check server logs
python -m agentrag.mcp_server 2>&1 | tee server.log

# Verify MCP protocol version
npm list -g @modelcontextprotocol/inspector
```

### Issue 3: Request Timeout

**Error:** Request takes too long

**Solution:**
```bash
# Check Qdrant connection
agentrag health

# Check embedding model
python -c "from agentrag.providers.embeddings import EmbeddingProvider; e = EmbeddingProvider('fastembed', 'jinaai/jina-embeddings-v2-base-code'); print(e.embed('test'))"
```

---

## 📊 Test Checklist

### ✅ Basic Tests
- [ ] Health check returns `ok: true`
- [ ] Query with natural language works
- [ ] Ingest dry-run shows expected chunks
- [ ] All 3 tools visible in inspector

### ✅ Advanced Tests
- [ ] Query with filters (node_type, language)
- [ ] Query with top_k parameter
- [ ] Ingest multiple targets
- [ ] Ingest URL (if internet available)

### ✅ Error Handling
- [ ] Empty query returns error
- [ ] Empty targets returns error
- [ ] Invalid node_type rejected
- [ ] Invalid access_level rejected

---

## 🎯 Expected Results

### Successful Test Session

```
✅ health_check
   → ok: true
   → collection_points: 22
   → embedding_dimensions: 768

✅ query_memory (natural)
   → total_hits: 3
   → fallback_used: false
   → hits contain relevant results

✅ query_memory (with filters)
   → node_type filter applied
   → language filter applied
   → results match criteria

✅ ingest_documents (dry-run)
   → new_chunks detected
   → stale_deleted calculated
   → dry_run: true
```

---

## 🚀 Next Steps

After successful testing with Inspector:

1. **Test with Real AI Agent**
   - Configure Kiro CLI
   - Test with Claude Desktop
   - Try with other MCP clients

2. **Production Deployment**
   - Remove dry-run flag
   - Ingest real documents
   - Monitor performance

3. **Integration**
   - Add to your application
   - Configure access levels
   - Setup monitoring

---

## 📚 References

- [MCP Inspector GitHub](https://github.com/modelcontextprotocol/inspector)
- [MCP Protocol Spec](https://modelcontextprotocol.io/)
- [agentRAG MCP Guide](MCP_SERVER_README.md)
- [agentRAG Testing Guide](MCP_TESTING.md)

---

## 💡 Tips

1. **Start Simple** - Test health_check first
2. **Use Dry-Run** - Always test ingest with dry_run=true first
3. **Check Logs** - Monitor server logs for errors
4. **Save Requests** - Use inspector history to save working queries
5. **Test Edge Cases** - Try empty inputs, invalid parameters
6. **Compare Results** - Test same query with different parameters

---

**Happy Testing!** 🎉
