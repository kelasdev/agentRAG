from __future__ import annotations

import re


_SAFEWORD_RE = re.compile(r"^\s*=+\s*BATAS\s*=+\s*$", flags=re.IGNORECASE)
_MD_HEADER_RE = re.compile(r"^\s{0,3}#{1,6}\s+\S+")


def _pack_paragraphs(paragraphs: list[str], max_chars: int) -> list[str]:
    if not paragraphs:
        return []

    chunks: list[str] = []
    buf = ""
    for para in paragraphs:
        candidate = para if not buf else f"{buf}\n\n{para}"
        if len(candidate) <= max_chars:
            buf = candidate
            continue
        if buf:
            chunks.append(buf)
        if len(para) <= max_chars:
            buf = para
            continue
        start = 0
        while start < len(para):
            chunks.append(para[start : start + max_chars])
            start += max_chars
        buf = ""

    if buf:
        chunks.append(buf)
    return chunks


def _split_sections(content: str) -> list[str]:
    text = content.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")
    sections: list[str] = []
    current: list[str] = []

    for ln in lines:
        if _SAFEWORD_RE.match(ln):
            if current and any(x.strip() for x in current):
                sections.append("\n".join(current).strip())
            current = []
            continue
        if _MD_HEADER_RE.match(ln):
            if current and any(x.strip() for x in current):
                sections.append("\n".join(current).strip())
                current = []
        current.append(ln)

    if current and any(x.strip() for x in current):
        sections.append("\n".join(current).strip())
    return sections


def chunk_text(content: str, max_chars: int = 1200) -> list[str]:
    # Safeword/markdown-header aware section split, then paragraph packing per section.
    sections = _split_sections(content)
    chunks: list[str] = []
    for section in sections:
        paragraphs = [p.strip() for p in section.split("\n\n") if p.strip()]
        chunks.extend(_pack_paragraphs(paragraphs, max_chars=max_chars))
    return chunks
