# MCP Inspector Test Scenarios

Copy-paste JSON berikut ke MCP Inspector untuk testing.

---

## 1. HEALTH CHECK

### Test: Basic Health Check
```json
{}
```

**Expected:** `ok: true`, `qdrant_ok: true`, `embedder_ok: true`

---

## 2. QUERY MEMORY

### Test 2.1: Natural Language - Find Python Function
```json
{
  "query": "python function untuk calculate ROI"
}
```

**Expected:** Auto-detects `node_type: code`, `language: python`

---

### Test 2.2: Natural Language - Find Documentation
```json
{
  "query": "installation guide documentation"
}
```

**Expected:** Auto-detects `node_type: text`

---

### Test 2.3: Natural Language - Bug Hunting
```json
{
  "query": "bug in authentication error"
}
```

**Expected:** Auto-detects `intent: bug_hunt`

---

### Test 2.4: Natural Language - Code Example
```json
{
  "query": "show javascript class for user authentication"
}
```

**Expected:** Auto-detects `node_type: code`, `language: javascript`

---

### Test 2.5: Manual Override - Force Python Code
```json
{
  "query": "calculate",
  "node_type": "code",
  "language": "python",
  "top_k": 5
}
```

**Expected:** Returns only Python code, max 5 results

---

### Test 2.6: Manual Override - Documentation Only
```json
{
  "query": "API endpoints",
  "node_type": "text",
  "top_k": 10
}
```

**Expected:** Returns only text/documentation

---

### Test 2.7: Access Level - Public Only
```json
{
  "query": "public documentation",
  "access_level": "public"
}
```

**Expected:** Returns only public documents

---

### Test 2.8: Empty Query (Error Test)
```json
{
  "query": ""
}
```

**Expected:** Error - "Query cannot be empty"

---

## 3. INGEST DOCUMENTS

### Test 3.1: Local File - Dry Run
```json
{
  "targets": ["/home/kelasdev/agentRAG/test_data/README.md"],
  "access_level": "internal",
  "dry_run": true
}
```

**Expected:** Shows `new_chunks`, `unchanged_chunks`, `stale_deleted`, `dry_run: true`

---

### Test 3.2: Multiple Local Files - Dry Run
```json
{
  "targets": [
    "/home/kelasdev/agentRAG/test_data/example.py",
    "/home/kelasdev/agentRAG/test_data/example.js"
  ],
  "dry_run": true
}
```

**Expected:** Processes multiple files

---

### Test 3.3: Directory - Dry Run
```json
{
  "targets": ["/home/kelasdev/agentRAG/test_data"],
  "dry_run": true
}
```

**Expected:** Recursively processes all files in directory

---

### Test 3.4: URL - Dry Run (Requires Internet)
```json
{
  "targets": ["https://raw.githubusercontent.com/qdrant/qdrant/master/README.md"],
  "dry_run": true
}
```

**Expected:** Fetches and processes URL content

---

### Test 3.5: Mixed Local + URL - Dry Run
```json
{
  "targets": [
    "/home/kelasdev/agentRAG/README.md",
    "https://raw.githubusercontent.com/qdrant/qdrant/master/README.md"
  ],
  "dry_run": true
}
```

**Expected:** Processes both local and URL targets

---

### Test 3.6: Public Access Level
```json
{
  "targets": ["/home/kelasdev/agentRAG/README.md"],
  "access_level": "public",
  "dry_run": true
}
```

**Expected:** Sets access_level to public

---

### Test 3.7: Empty Targets (Error Test)
```json
{
  "targets": []
}
```

**Expected:** Error - "Targets cannot be empty"

---

### Test 3.8: Real Ingest (No Dry Run)
```json
{
  "targets": ["/home/kelasdev/agentRAG/test_data/example.py"],
  "access_level": "internal",
  "dry_run": false
}
```

**Expected:** Actually writes to Qdrant, `dry_run: false`

---

## 4. ADVANCED SCENARIOS

### Test 4.1: Query After Ingest
**Step 1:** Ingest
```json
{
  "targets": ["/home/kelasdev/agentRAG/test_data/example.py"],
  "dry_run": false
}
```

**Step 2:** Query
```json
{
  "query": "python function hello"
}
```

**Expected:** Finds the ingested function

---

### Test 4.2: Fallback Strategy Test
```json
{
  "query": "very specific function that probably does not exist xyz123"
}
```

**Expected:** `fallback_used: true`, returns best available results

---

### Test 4.3: Large Top-K
```json
{
  "query": "test",
  "top_k": 20
}
```

**Expected:** Returns up to 20 results

---

### Test 4.4: Language-Specific Search
```json
{
  "query": "function",
  "language": "javascript"
}
```

**Expected:** Returns only JavaScript functions

---

### Test 4.5: Multi-Language Query
```json
{
  "query": "contoh kode python untuk testing"
}
```

**Expected:** Handles Indonesian + English mixed query

---

## 5. PERFORMANCE TESTS

### Test 5.1: Quick Query
```json
{
  "query": "test"
}
```

**Expected:** Response < 2 seconds

---

### Test 5.2: Complex Query
```json
{
  "query": "python function untuk calculate ROI dengan error handling dan logging"
}
```

**Expected:** Response < 3 seconds

---

### Test 5.3: Large Ingest (Dry Run)
```json
{
  "targets": ["/home/kelasdev/agentRAG"],
  "dry_run": true
}
```

**Expected:** Processes entire directory, shows total chunks

---

## 6. ERROR HANDLING TESTS

### Test 6.1: Invalid Node Type
```json
{
  "query": "test",
  "node_type": "invalid"
}
```

**Expected:** Schema validation error

---

### Test 6.2: Invalid Access Level
```json
{
  "query": "test",
  "access_level": "invalid"
}
```

**Expected:** Schema validation error

---

### Test 6.3: Non-Existent File
```json
{
  "targets": ["/path/that/does/not/exist.txt"],
  "dry_run": true
}
```

**Expected:** Skipped count increases

---

### Test 6.4: Invalid URL
```json
{
  "targets": ["https://this-url-does-not-exist-xyz123.com"],
  "dry_run": true
}
```

**Expected:** Skipped count increases

---

## 📊 EXPECTED RESULTS SUMMARY

| Test | Expected Result |
|------|----------------|
| Health Check | `ok: true` |
| Natural Query | Auto-classification works |
| Manual Override | Filters applied correctly |
| Dry Run Ingest | Shows chunk counts |
| Real Ingest | Writes to Qdrant |
| Empty Input | Error message |
| Invalid Enum | Schema validation error |
| Fallback | Returns best available |

---

## 💡 TIPS

1. **Start Simple** - Test health_check first
2. **Use Dry Run** - Always test ingest with `dry_run: true` first
3. **Check Response** - Verify `ok`, `total_hits`, `dry_run` fields
4. **Test Errors** - Try invalid inputs to verify error handling
5. **Compare Results** - Test same query with different parameters
6. **Save History** - Inspector saves your test history

---

**Happy Testing!** 🎉
