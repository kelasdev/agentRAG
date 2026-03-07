from __future__ import annotations

import ast
import re
from dataclasses import dataclass

try:
    from tree_sitter_languages import get_parser as _get_ts_parser
except Exception:  # pragma: no cover - optional dependency runtime guard
    _get_ts_parser = None


@dataclass
class CodeChunk:
    content: str
    ast_type: str | None
    symbol_name: str | None
    line_start: int | None
    line_end: int | None
    parameters: list[dict[str, str | None]] | None
    calls: list[str] | None
    docstring: str | None


def _chunk_python(code: str) -> list[CodeChunk]:
    module = ast.parse(code)
    lines = code.splitlines()
    chunks: list[CodeChunk] = []

    for node in module.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Import, ast.ImportFrom)):
            continue

        start = getattr(node, "lineno", None)
        end = getattr(node, "end_lineno", None)
        snippet = ""
        if start and end:
            snippet = "\n".join(lines[start - 1 : end])

        ast_type = type(node).__name__
        symbol_name = getattr(node, "name", None)
        parameters = None
        calls = None
        docstring = ast.get_docstring(node) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) else None

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            parameters = [{"name": a.arg, "type": getattr(a.annotation, "id", None)} for a in node.args.args]
            calls = sorted(
                {
                    n.func.id
                    for n in ast.walk(node)
                    if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                }
            )

        chunks.append(
            CodeChunk(
                content=snippet or ast.get_source_segment(code, node) or "",
                ast_type=ast_type,
                symbol_name=symbol_name,
                line_start=start,
                line_end=end,
                parameters=parameters,
                calls=calls,
                docstring=docstring,
            )
        )

    if not chunks:
        return [
            CodeChunk(
                content=code,
                ast_type=None,
                symbol_name=None,
                line_start=None,
                line_end=None,
                parameters=None,
                calls=None,
                docstring=None,
            )
        ]
    return chunks


_TS_NODE_TYPES: dict[str, dict[str, str]] = {
    "javascript": {
        "import_statement": "ImportDeclaration",
        "function_declaration": "FunctionDeclaration",
        "generator_function_declaration": "FunctionDeclaration",
        "class_declaration": "ClassDeclaration",
    },
    "typescript": {
        "import_statement": "ImportDeclaration",
        "function_declaration": "FunctionDeclaration",
        "generator_function_declaration": "FunctionDeclaration",
        "class_declaration": "ClassDeclaration",
    },
    "go": {
        "import_declaration": "ImportSpec",
        "function_declaration": "FuncDecl",
        "method_declaration": "FuncDecl",
        "type_declaration": "TypeSpec",
    },
    "java": {
        "import_declaration": "ImportDeclaration",
        "class_declaration": "TypeDeclaration",
        "interface_declaration": "TypeDeclaration",
        "enum_declaration": "TypeDeclaration",
        "record_declaration": "TypeDeclaration",
        "annotation_type_declaration": "TypeDeclaration",
        "method_declaration": "MethodDeclaration",
        "constructor_declaration": "MethodDeclaration",
    },
}


def _extract_parameters(raw: str) -> list[dict[str, str | None]]:
    body = raw.strip()
    if body.startswith("(") and body.endswith(")"):
        body = body[1:-1]
    parts = [p.strip() for p in body.split(",") if p.strip()]
    out: list[dict[str, str | None]] = []
    for p in parts:
        token = re.split(r"\s+", p)[-1]
        token = token.lstrip("*\u0026")
        token = token.split(":", 1)[0].strip()
        if token:
            out.append({"name": token, "type": None})
    return out


def _walk_tree(node):
    stack = [node]
    while stack:
        current = stack.pop()
        yield current
        # Keep source order by pushing reversed children.
        children = list(current.children)
        for child in reversed(children):
            stack.append(child)


def _chunk_tree_sitter(code: str, language: str) -> list[CodeChunk] | None:
    if _get_ts_parser is None:
        return None

    type_map = _TS_NODE_TYPES.get(language)
    if not type_map:
        return None

    try:
        parser = _get_ts_parser(language)
    except Exception:
        return None

    code_bytes = code.encode("utf-8")
    tree = parser.parse(code_bytes)
    root = tree.root_node

    chunks: list[CodeChunk] = []
    for node in _walk_tree(root):
        mapped_type = type_map.get(node.type)
        if not mapped_type:
            continue

        snippet = code_bytes[node.start_byte : node.end_byte].decode("utf-8", errors="ignore")
        name_node = node.child_by_field_name("name")
        params_node = node.child_by_field_name("parameters")

        symbol_name = None
        if name_node is not None:
            symbol_name = code_bytes[name_node.start_byte : name_node.end_byte].decode(
                "utf-8", errors="ignore"
            )

        parameters = None
        if mapped_type in {"FunctionDeclaration", "FuncDecl", "MethodDeclaration"} and params_node is not None:
            raw_params = code_bytes[params_node.start_byte : params_node.end_byte].decode(
                "utf-8", errors="ignore"
            )
            extracted = _extract_parameters(raw_params)
            parameters = extracted or None

        chunks.append(
            CodeChunk(
                content=snippet,
                ast_type=mapped_type,
                symbol_name=symbol_name,
                line_start=node.start_point[0] + 1,
                line_end=node.end_point[0] + 1,
                parameters=parameters,
                calls=None,
                docstring=None,
            )
        )

    if chunks:
        return chunks
    return None


def _extract_brace_block(lines: list[str], start_idx: int) -> tuple[int, str]:
    """Fallback extractor when tree-sitter is unavailable."""
    brace_balance = 0
    started = False
    end_idx = start_idx

    for i in range(start_idx, len(lines)):
        line = lines[i]
        opens = line.count("{")
        closes = line.count("}")
        if opens > 0:
            started = True
        if started:
            brace_balance += opens - closes
            end_idx = i
            if brace_balance <= 0:
                break
        elif i > start_idx:
            break

    snippet = "\n".join(lines[start_idx : end_idx + 1]).strip()
    return end_idx, snippet


def _chunk_cstyle_fallback(code: str, language: str) -> list[CodeChunk]:
    lines = code.splitlines()
    chunks: list[CodeChunk] = []

    if language in {"javascript", "typescript"}:
        rules = [
            (re.compile(r"^\s*import\b"), "ImportDeclaration", None),
            (re.compile(r"^\s*(?:export\s+)?function\s+([A-Za-z_][\w$]*)\s*\("), "FunctionDeclaration", "brace"),
            (re.compile(r"^\s*class\s+([A-Za-z_][\w$]*)\b"), "ClassDeclaration", "brace"),
        ]
    elif language == "go":
        rules = [
            (re.compile(r"^\s*import\b"), "ImportSpec", None),
            (re.compile(r"^\s*type\s+([A-Za-z_][\w]*)\b"), "TypeSpec", "brace"),
            (re.compile(r"^\s*func\s*(?:\([^)]*\))?\s*([A-Za-z_][\w]*)\s*\("), "FuncDecl", "brace"),
        ]
    elif language == "java":
        rules = [
            (re.compile(r"^\s*import\b"), "ImportDeclaration", None),
            (re.compile(r"^\s*(?:public\s+)?(?:class|interface|enum)\s+([A-Za-z_][\w]*)\b"), "TypeDeclaration", "brace"),
            (
                re.compile(
                    r"^\s*(?:public|private|protected)?\s*(?:static\s+)?(?:final\s+)?[\w<>\[\]]+\s+([A-Za-z_][\w]*)\s*\([^;]*\)\s*\{"
                ),
                "MethodDeclaration",
                "brace",
            ),
        ]
    else:
        rules = []

    for idx, line in enumerate(lines):
        for pattern, ast_type, body_mode in rules:
            m = pattern.match(line)
            if not m:
                continue

            symbol_name = m.group(1) if m.lastindex else None
            line_start = idx + 1
            if body_mode == "brace":
                end_idx, snippet = _extract_brace_block(lines, idx)
                line_end = end_idx + 1
            else:
                snippet = line.strip()
                line_end = line_start

            chunks.append(
                CodeChunk(
                    content=snippet,
                    ast_type=ast_type,
                    symbol_name=symbol_name,
                    line_start=line_start,
                    line_end=line_end,
                    parameters=None,
                    calls=None,
                    docstring=None,
                )
            )
            break

    if chunks:
        return chunks

    return [
        CodeChunk(
            content=code,
            ast_type=None,
            symbol_name=None,
            line_start=None,
            line_end=None,
            parameters=None,
            calls=None,
            docstring=None,
        )
    ]


def chunk_code(content: str, language: str) -> list[CodeChunk]:
    if language == "python":
        return _chunk_python(content)
    if language in {"javascript", "typescript", "go", "java"}:
        ts_chunks = _chunk_tree_sitter(content, language)
        if ts_chunks is not None:
            return ts_chunks
        return _chunk_cstyle_fallback(content, language)
    return [
        CodeChunk(
            content=content,
            ast_type=None,
            symbol_name=None,
            line_start=None,
            line_end=None,
            parameters=None,
            calls=None,
            docstring=None,
        )
    ]
