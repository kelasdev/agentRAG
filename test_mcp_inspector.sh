#!/bin/bash

# MCP Inspector Quick Start Script
# Usage: ./test_mcp_inspector.sh

set -e

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║         agentRAG MCP Inspector - Quick Start                 ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo "❌ npm not found. Please install Node.js first:"
    echo "   https://nodejs.org/"
    exit 1
fi

echo "✅ npm found: $(npm --version)"
echo ""

# Check if npx is available
if ! command -v npx &> /dev/null; then
    echo "❌ npx not found. Please update npm:"
    echo "   npm install -g npm@latest"
    exit 1
fi

echo "✅ npx found"
echo ""

# Check if Python virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Virtual environment not activated"
    echo "   Activating .venv..."
    source .venv/bin/activate
fi

echo "✅ Virtual environment: $VIRTUAL_ENV"
echo ""

# Check if agentrag is installed
if ! python -c "import agentrag" 2>/dev/null; then
    echo "❌ agentRAG not installed. Installing..."
    pip install -e .
fi

echo "✅ agentRAG installed"
echo ""

# Check environment variables
if [ ! -f .env ]; then
    echo "❌ .env file not found. Please create it from .env.example"
    exit 1
fi

echo "✅ .env file found"
echo ""

# Check Qdrant connection
echo "🔍 Checking Qdrant connection..."
if python -c "from agentrag.config import get_settings; from agentrag.qdrant_store import QdrantStore; from agentrag.providers.embeddings import EmbeddingProvider; s = get_settings(); e = EmbeddingProvider(s.embedding_provider, s.embedding_model); store = QdrantStore(s.qdrant_url, s.qdrant_api_key, s.collection_name, e.dimensions); print('OK' if store.health_check() else 'FAIL')" 2>/dev/null | grep -q "OK"; then
    echo "✅ Qdrant connection OK"
else
    echo "❌ Qdrant connection failed. Check your .env settings"
    exit 1
fi

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                  Starting MCP Inspector                      ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "📋 Available Tools:"
echo "   1. query_memory      - Search the RAG memory"
echo "   2. ingest_documents  - Add documents to memory"
echo "   3. health_check      - Check system health"
echo ""
echo "🌐 Inspector will open in your browser at:"
echo "   http://localhost:5173"
echo ""
echo "💡 Tips:"
echo "   - Start with health_check to verify connection"
echo "   - Use dry_run=true for ingest testing"
echo "   - Try natural language queries"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""
echo "════════════════════════════════════════════════════════════════"
echo ""

# Start MCP Inspector
npx @modelcontextprotocol/inspector python -m agentrag.mcp_server
