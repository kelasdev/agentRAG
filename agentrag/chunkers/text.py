from __future__ import annotations


def chunk_text(content: str, max_chars: int = 1200) -> list[str]:
    # Split by paragraph boundaries first, then pack into bounded chunks.
    paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
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
