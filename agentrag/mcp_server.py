"""MCP Server for agentRAG integration with AI agents."""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    ListToolsRequest,
    Tool,
    TextContent,
)

from agentrag.config import get_settings
from agentrag.ingest import ingest_paths, ingest_urls
from agentrag.pipeline import run_query_pipeline
from agentrag.providers.embeddings import EmbeddingProvider
from agentrag.qdrant_store import QdrantStore

logger = logging.getLogger(__name__)

# Create server instance
server = Server("agentrag")


@server.list_tools()
async def list_tools() -> List[Tool]:
    """List available tools."""
    return [
        Tool(
            name="query_memory",
            description="Query the agentRAG memory system for relevant information",
            inputSchema={
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
                        "description": "Filter by node type: 'text' or 'code' (optional)",
                        "enum": ["text", "code"]
                    },
                    "language": {
                        "type": "string",
                        "description": "Filter by programming language (e.g., 'python', 'javascript') (optional)"
                    },
                    "access_level": {
                        "type": "string",
                        "description": "Filter by access level: 'public', 'internal', 'admin' (optional)",
                        "default": "internal"
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="ingest_documents",
            description="Ingest documents into the agentRAG memory system",
            inputSchema={
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
                        "default": False
                    }
                },
                "required": ["targets"]
            }
        ),
        Tool(
            name="health_check",
            description="Check the health of the agentRAG system",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="code_graph",
            description="Code graph navigation using Qdrant payload filters (definitions/callers/callees)",
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "Graph action",
                        "enum": ["definitions", "callers", "callees"]
                    },
                    "symbol": {
                        "type": "string",
                        "description": "Symbol name (function/class/method)"
                    },
                    "language": {
                        "type": "string",
                        "description": "Optional language filter (e.g. python)"
                    },
                    "access_level": {
                        "type": "string",
                        "description": "Filter by access level",
                        "default": "internal",
                        "enum": ["public", "internal", "admin"]
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max number of records to return/inspect",
                        "default": 25
                    }
                },
                "required": ["action", "symbol"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
    """Handle tool calls."""
    try:
        settings = get_settings()
        
        # Initialize embedder and store for all operations
        embedder = EmbeddingProvider(
            provider=settings.embedding_provider,
            model_name=settings.embedding_model,
            model_path=settings.llama_cpp_embed_model_path,
            n_threads=settings.llama_cpp_n_threads,
            openai_base_url=settings.openai_compatible_base_url,
            openai_api_key=settings.openai_compatible_api_key,
            request_timeout_seconds=settings.embedding_request_timeout_seconds,
        )
        
        store = QdrantStore(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
            collection_name=settings.collection_name,
            vector_size=embedder.dimensions,
        )

        if name == "query_memory":
            return await _handle_query_memory(arguments, embedder, store)
        elif name == "ingest_documents":
            return await _handle_ingest_documents(arguments, embedder, store)
        elif name == "health_check":
            return await _handle_health_check(embedder, store)
        elif name == "code_graph":
            return await _handle_code_graph(arguments, store)
        else:
            raise ValueError(f"Unknown tool: {name}")
            
    except Exception as e:
        logger.error(f"Tool call failed for {name}: {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def _handle_query_memory(arguments: Dict[str, Any], embedder: EmbeddingProvider, store: QdrantStore) -> List[TextContent]:
    """Handle query_memory tool call."""
    query = arguments.get("query", "")
    top_k = arguments.get("top_k", 3)
    node_type = arguments.get("node_type")
    language = arguments.get("language")
    access_level = arguments.get("access_level", "internal")
    
    # Validate query
    if not query.strip():
        raise ValueError("Query cannot be empty")
    
    # Run query pipeline
    result = run_query_pipeline(
        query=query,
        settings=get_settings(),
        embedder=embedder,
        store=store,
        top_k=top_k,
        node_type=node_type,
        language=language,
        access_level=access_level,
    )
    
    # Format results
    hits_data = []
    for hit in result.hits:
        payload = hit.payload or {}
        hit_info = {
            "rank": hit.score,
            "source_id": payload.get("source_id"),
            "hierarchy_path": payload.get("hierarchy_path"),
            "content": payload.get("content", ""),
            "node_type": payload.get("node_type"),
            "score": float(hit.score),
        }
        
        # Add language if available
        if payload.get("code_metadata"):
            hit_info["language"] = payload["code_metadata"].get("language")
            hit_info["symbol_name"] = payload["code_metadata"].get("symbol_name")
        
        hits_data.append(hit_info)
    
    response = {
        "query": query,
        "total_hits": len(hits_data),
        "fallback_used": result.fallback_used,
        "final_top_k": result.final_top_k,
        "hits": hits_data
    }
    
    return [TextContent(type="text", text=json.dumps(response, ensure_ascii=True, indent=2))]


async def _handle_ingest_documents(arguments: Dict[str, Any], embedder: EmbeddingProvider, store: QdrantStore) -> List[TextContent]:
    """Handle ingest_documents tool call."""
    targets = arguments.get("targets", [])
    access_level = arguments.get("access_level", "internal")
    dry_run = arguments.get("dry_run", False)
    
    if not targets:
        raise ValueError("Targets cannot be empty")
    
    # Separate files/directories from URLs
    paths = []
    urls = []
    
    for target in targets:
        if target.startswith(("http://", "https://")):
            urls.append(target)
        else:
            paths.append(target)
    
    # Process paths
    result = None
    if paths:
        from pathlib import Path
        path_objects = []
        for path_str in paths:
            path = Path(path_str)
            if path.exists():
                path_objects.append(path)
        
        if path_objects:
            result = ingest_paths(
                paths=path_objects,
                store=store,
                embedder=embedder,
                access_level=access_level,
                dry_run=dry_run,
            )
    
    # Process URLs
    urls_result = None
    if urls:
        urls_result = ingest_urls(
            urls=urls,
            store=store,
            embedder=embedder,
            access_level=access_level,
            dry_run=dry_run,
            jina_reader_base_url=get_settings().jina_reader_base_url,
            request_timeout_seconds=get_settings().web_fetch_timeout_seconds,
        )
    
    # Combine results
    if result and urls_result:
        combined_result = {
            "nodes_created": result.nodes_created + urls_result.nodes_created,
            "skipped": result.skipped + urls_result.skipped,
            "new_chunks": result.new_chunks + urls_result.new_chunks,
            "unchanged_chunks": result.unchanged_chunks + urls_result.unchanged_chunks,
            "stale_deleted": result.stale_deleted + urls_result.stale_deleted,
            "dry_run": dry_run
        }
    elif result:
        combined_result = {
            "nodes_created": result.nodes_created,
            "skipped": result.skipped,
            "new_chunks": result.new_chunks,
            "unchanged_chunks": result.unchanged_chunks,
            "stale_deleted": result.stale_deleted,
            "dry_run": dry_run
        }
    elif urls_result:
        combined_result = {
            "nodes_created": urls_result.nodes_created,
            "skipped": urls_result.skipped,
            "new_chunks": urls_result.new_chunks,
            "unchanged_chunks": urls_result.unchanged_chunks,
            "stale_deleted": urls_result.stale_deleted,
            "dry_run": dry_run
        }
    else:
        combined_result = {"message": "No valid targets found", "dry_run": dry_run}
    
    return [TextContent(type="text", text=json.dumps(combined_result, ensure_ascii=True, indent=2))]


async def _handle_health_check(embedder: EmbeddingProvider, store: QdrantStore) -> List[TextContent]:
    """Handle health_check tool call."""
    # Check Qdrant connection
    qdrant_ok = store.health_check()
    
    # Check embedder
    embedder_ok = True
    try:
        # Test with a simple query
        test_embedding = embedder.embed("test")
        embedder_ok = len(test_embedding) > 0
    except Exception:
        embedder_ok = False
    
    # Check collection
    collection_exists = False
    collection_points = 0
    if qdrant_ok:
        try:
            collections = store.client.get_collections().collections
            collection_names = {c.name for c in collections}
            if store.collection_name in collection_names:
                collection_exists = True
                count_response = store.count()
                collection_points = int(getattr(count_response, "count", 0) or 0)
        except Exception:
            collection_exists = False
    
    health_status = {
        "ok": qdrant_ok and embedder_ok,
        "qdrant_ok": qdrant_ok,
        "embedder_ok": embedder_ok,
        "collection_exists": collection_exists,
        "collection_points": collection_points,
        "collection_name": store.collection_name,
        "embedding_provider": embedder.provider,
        "embedding_dimensions": embedder.dimensions
    }
    
    return [TextContent(type="text", text=json.dumps(health_status, ensure_ascii=True, indent=2))]


async def _handle_code_graph(arguments: Dict[str, Any], store: QdrantStore) -> List[TextContent]:
    """Handle code_graph tool call using payload-only graph queries."""
    store.ensure_payload_indexes()
    action = (arguments.get("action") or "").strip().lower()
    symbol = (arguments.get("symbol") or "").strip()
    language = arguments.get("language")
    access_level = arguments.get("access_level", "internal")
    limit = int(arguments.get("limit", 25) or 25)

    if not action or action not in {"definitions", "callers", "callees"}:
        raise ValueError("action must be one of: definitions, callers, callees")
    if not symbol:
        raise ValueError("symbol cannot be empty")

    if action == "definitions":
        points = store.find_definitions(
            symbol_name=symbol,
            language=language,
            access_level=access_level,
            limit=limit,
        )
        out = {
            "action": action,
            "symbol": symbol,
            "language": language,
            "access_level": access_level,
            "count": len(points),
            "definitions": [{"id": getattr(p, "id", None), "payload": getattr(p, "payload", None)} for p in points],
        }
        return [TextContent(type="text", text=json.dumps(out, ensure_ascii=True, indent=2))]

    if action == "callers":
        points = store.find_callers(
            callee_symbol_name=symbol,
            language=language,
            access_level=access_level,
            limit=limit,
        )
        out = {
            "action": action,
            "callee_symbol": symbol,
            "language": language,
            "access_level": access_level,
            "count": len(points),
            "callers": [{"id": getattr(p, "id", None), "payload": getattr(p, "payload", None)} for p in points],
        }
        return [TextContent(type="text", text=json.dumps(out, ensure_ascii=True, indent=2))]

    # action == "callees"
    defs = store.find_definitions(
        symbol_name=symbol,
        language=language,
        access_level=access_level,
        limit=limit,
    )
    callees: list[str] = []
    for p in defs:
        payload = getattr(p, "payload", None) or {}
        code_meta = payload.get("code_metadata") or {}
        raw_calls = code_meta.get("calls") or []
        for c in raw_calls:
            if isinstance(c, str) and c not in callees:
                callees.append(c)
    out = {
        "action": action,
        "caller_symbol": symbol,
        "language": language,
        "access_level": access_level,
        "definitions_count": len(defs),
        "callees": callees,
    }
    return [TextContent(type="text", text=json.dumps(out, ensure_ascii=True, indent=2))]


async def main():
    """Run the MCP server."""
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    # Run with stdio
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
