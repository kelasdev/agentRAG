from agentrag.chunkers.code import chunk_code
from agentrag.chunkers.text import chunk_text


def test_chunk_text_respects_boundaries():
    content = "A" * 20 + "\n\n" + "B" * 20 + "\n\n" + "C" * 20
    chunks = chunk_text(content, max_chars=30)
    assert len(chunks) >= 2
    assert all(len(c) <= 30 for c in chunks)


def test_chunk_code_python_extracts_symbols():
    code = """
import os

def calculate_roi(gain, cost):
    return (gain - cost) / cost

class Foo:
    def bar(self):
        return calculate_roi(10, 5)
"""
    chunks = chunk_code(code, language="python")
    ast_types = {c.ast_type for c in chunks}
    assert "Import" in ast_types
    assert "FunctionDef" in ast_types
    assert "ClassDef" in ast_types


def test_chunk_code_js_extracts_structural_types():
    code = """
import x from \"y\";

function add(a, b) {
  return a + b;
}

class MathOps {
  mul(a, b) {
    return a * b;
  }
}
"""
    chunks = chunk_code(code, language="javascript")
    ast_types = {c.ast_type for c in chunks}
    assert "ImportDeclaration" in ast_types
    assert "FunctionDeclaration" in ast_types
    assert "ClassDeclaration" in ast_types
