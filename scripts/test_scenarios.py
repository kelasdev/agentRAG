#!/usr/bin/env python3
"""
Comprehensive test scenarios for agentRAG MCP server.
Tests various query types, edge cases, and error handling.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agentrag.mcp_server import call_tool


def print_section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


async def test_scenario(name: str, tool_name: str, args: dict):
    print(f"\n--- {name} ---")
    print(f"Tool: {tool_name}")
    print(f"Input: {json.dumps(args, indent=2)}")
    
    try:
        result = await call_tool(tool_name, args)
        print(f"✓ Success")
        # Extract text content from result
        if hasattr(result, 'content') and result.content:
            content = result.content[0].text if result.content else ""
            print(f"Output: {content[:500]}...")
        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False


async def main():
    results = []
    
    # Health Check
    print_section("1. Health Check")
    results.append(await test_scenario(
        "Basic health check",
        "health_check",
        {}
    ))
    
    # Query Scenarios
    print_section("2. Query Memory - Code Search")
    
    results.append(await test_scenario(
        "Python function search",
        "query_memory",
        {"query": "python function calculate", "top_k": 3}
    ))
    
    results.append(await test_scenario(
        "JavaScript class search",
        "query_memory",
        {"query": "javascript class UserService", "top_k": 3}
    ))
    
    results.append(await test_scenario(
        "Bug hunting query",
        "query_memory",
        {"query": "bug in authentication error handling", "top_k": 5}
    ))
    
    print_section("3. Query Memory - Documentation Search")
    
    results.append(await test_scenario(
        "Documentation search",
        "query_memory",
        {"query": "how to install and setup", "node_type": "text", "top_k": 3}
    ))
    
    results.append(await test_scenario(
        "API documentation",
        "query_memory",
        {"query": "API reference for query", "node_type": "text", "top_k": 3}
    ))
    
    print_section("4. Query Memory - Filters")
    
    results.append(await test_scenario(
        "Language filter",
        "query_memory",
        {"query": "function example", "language": "python", "top_k": 3}
    ))
    
    results.append(await test_scenario(
        "Access level filter",
        "query_memory",
        {"query": "test data", "access_level": "internal", "top_k": 3}
    ))
    
    print_section("5. Query Memory - Edge Cases")
    
    results.append(await test_scenario(
        "Empty query",
        "query_memory",
        {"query": "", "top_k": 3}
    ))
    
    results.append(await test_scenario(
        "Very long query",
        "query_memory",
        {"query": "a " * 100, "top_k": 3}
    ))
    
    results.append(await test_scenario(
        "Special characters",
        "query_memory",
        {"query": "function @#$% test", "top_k": 3}
    ))
    
    print_section("6. Ingest - Dry Run")
    
    results.append(await test_scenario(
        "Dry run ingest",
        "ingest_documents",
        {"targets": ["test_data/example.py"], "dry_run": True}
    ))
    
    print_section("7. Error Handling")
    
    results.append(await test_scenario(
        "Invalid top_k",
        "query_memory",
        {"query": "test", "top_k": -1}
    ))
    
    results.append(await test_scenario(
        "Invalid node_type",
        "query_memory",
        {"query": "test", "node_type": "invalid"}
    ))
    
    results.append(await test_scenario(
        "Missing required field",
        "query_memory",
        {"top_k": 3}  # Missing query
    ))
    
    # Summary
    print_section("Test Summary")
    passed = sum(results)
    total = len(results)
    print(f"\n✓ Passed: {passed}/{total}")
    print(f"✗ Failed: {total - passed}/{total}")
    
    if passed == total:
        print("\n🎉 All scenarios passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} scenario(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
