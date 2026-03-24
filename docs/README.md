# agentRAG Documentation

Dokumentasi lengkap untuk agentRAG - Intelligent Memory System for AI Agents.

## 📚 Table of Contents

### Getting Started
- [QUICKSTART.md](QUICKSTART.md) - Quick start guide untuk memulai menggunakan agentRAG
- [VECTOR_DIMENSIONS.md](VECTOR_DIMENSIONS.md) - Memahami dimensi vektor dan embedding models

### Product & Architecture
- [PRD.md](PRD.md) - Product Requirements Document
- [CORE_READINESS.md](CORE_READINESS.md) - Production readiness checklist
- [PROJECT_REVIEW.md](PROJECT_REVIEW.md) - Project review dan status

### MCP Server Integration
- [MCP_SERVER_README.md](MCP_SERVER_README.md) - Complete MCP server guide
- [MCP_QUICK_REF.md](MCP_QUICK_REF.md) - Quick reference untuk MCP tools
- [MCP_TESTING.md](MCP_TESTING.md) - Comprehensive testing guide
- [MCP_INSPECTOR_GUIDE.md](MCP_INSPECTOR_GUIDE.md) - Visual testing dengan MCP Inspector
- [MCP_INSPECTOR_TEST_SCENARIOS.md](MCP_INSPECTOR_TEST_SCENARIOS.md) - Test scenarios untuk MCP Inspector
- [MCP_SERVER_TESTING_SUMMARY.md](MCP_SERVER_TESTING_SUMMARY.md) - Testing summary

### Testing & Quality
- [TEST_REPORT.md](TEST_REPORT.md) - Detailed test results dan coverage analysis

## 🔗 Quick Links

**Main Documentation:** [../README.md](../README.md)

**Key Features:**
- 🧠 Automatic Query Planning
- 🔄 Smart Fallback Strategy
- 📦 Hybrid Chunking (AST-based for code, delimiter-based for text)
- 🔌 MCP Server Integration
- ⚡ Delta Sync
- 🌐 URL Ingest

**Installation:**
```bash
pip install -r requirements.txt
pip install -e .
```

**Quick Start:**
```bash
# Ingest documents
agentrag ingest docs/PRD.md

# Watch local changes
agentrag watch ./docs

# Query memory
agentrag query "qdrant cloud url" --node-type text --top-k 3

# Health check
agentrag health
```

## 📖 Documentation Structure

```
docs/
├── README.md                           # This file
├── QUICKSTART.md                       # Quick start guide
├── VECTOR_DIMENSIONS.md                # Vector dimensions explained
├── PRD.md                              # Product requirements
├── CORE_READINESS.md                   # Production readiness
├── PROJECT_REVIEW.md                   # Project review
├── MCP_SERVER_README.md                # MCP server guide
├── MCP_QUICK_REF.md                    # MCP quick reference
├── MCP_TESTING.md                      # MCP testing guide
├── MCP_INSPECTOR_GUIDE.md              # MCP Inspector guide
├── MCP_INSPECTOR_TEST_SCENARIOS.md     # MCP test scenarios
├── MCP_SERVER_TESTING_SUMMARY.md       # MCP testing summary
└── TEST_REPORT.md                      # Test report
```

## 🤝 Contributing

Contributions are welcome! Please read the main [README.md](../README.md) for contribution guidelines.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](../LICENSE) file for details.
