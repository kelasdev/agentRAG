from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal


Intent = Literal["find_snippet", "explain_function", "bug_hunt", "refactor_guidance", "general_query"]


@dataclass
class QueryPlan:
    intent: Intent
    node_type: str | None
    language: str | None
    symbol_name: str | None
    access_level: str | None


LANG_HINTS: dict[str, str] = {
    "python": "python",
    "py": "python",
    "javascript": "javascript",
    "typescript": "typescript",
    "java": "java",
    "golang": "go",
    "go": "go",
    "rust": "rust",
    "cpp": "cpp",
    "c++": "cpp",
    "c": "c",
}


def build_query_plan(query: str) -> QueryPlan:
    q = query.lower()
    intent: Intent = "general_query"
    if any(k in q for k in ["function", "class", "method", "def "]):
        intent = "explain_function"
    elif any(k in q for k in ["bug", "error", "exception", "traceback", "fix"]):
        intent = "bug_hunt"
    elif any(k in q for k in ["refactor", "improve design", "clean code"]):
        intent = "refactor_guidance"
    elif any(k in q for k in ["snippet", "show code", "contoh kode"]):
        intent = "find_snippet"

    node_type = None
    if any(k in q for k in ["code", "function", "class", "method", "snippet"]):
        node_type = "code"
    elif any(k in q for k in ["docs", "documentation", "guide", "markdown", "txt"]):
        node_type = "text"

    language = _extract_language(q)
    symbol_name = _extract_symbol_name(q)
    access_level = "internal"

    return QueryPlan(
        intent=intent,
        node_type=node_type,
        language=language,
        symbol_name=symbol_name,
        access_level=access_level,
    )


def _extract_symbol_name(query: str) -> str | None:
    if "symbol:" in query:
        value = query.split("symbol:", 1)[1].strip().split()[0]
        return value.strip("`'\".,:;()[]{}")
    # Support natural query forms: "function foo", "class Bar", "method baz"
    m = re.search(r"\b(?:function|class|method|symbol)\s+([A-Za-z_][\w]*)\b", query)
    if m:
        return m.group(1)
    return None


def _extract_language(query: str) -> str | None:
    for key, lang in LANG_HINTS.items():
        if re.search(rf"\b{re.escape(key)}\b", query):
            return lang
    return None
