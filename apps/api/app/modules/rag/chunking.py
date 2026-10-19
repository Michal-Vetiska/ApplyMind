"""Document chunking utilities."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class TextChunk:
    content: str
    chunk_index: int
    section_heading: str | None
    token_count: int


def estimate_tokens(text: str) -> int:
    return max(1, len(text.split()))


def chunk_text(
    text: str,
    *,
    chunk_size: int = 500,
    overlap: int = 80,
) -> list[TextChunk]:
    cleaned = re.sub(r"\r\n?", "\n", text).strip()
    if not cleaned:
        return []

    paragraphs = [p.strip() for p in re.split(r"\n{2,}", cleaned) if p.strip()]
    chunks: list[TextChunk] = []
    buffer = ""
    heading: str | None = None
    index = 0

    def flush(buf: str, head: str | None) -> None:
        nonlocal index
        content = buf.strip()
        if not content:
            return
        chunks.append(
            TextChunk(
                content=content,
                chunk_index=index,
                section_heading=head,
                token_count=estimate_tokens(content),
            )
        )
        index += 1

    for para in paragraphs:
        if len(para) < 80 and not para.endswith("."):
            heading = para
        candidate = f"{buffer}\n\n{para}".strip() if buffer else para
        if estimate_tokens(candidate) > chunk_size and buffer:
            flush(buffer, heading)
            # overlap
            words = buffer.split()
            tail = " ".join(words[-overlap:]) if len(words) > overlap else buffer
            buffer = f"{tail}\n\n{para}".strip()
        else:
            buffer = candidate

    flush(buffer, heading)
    return chunks
