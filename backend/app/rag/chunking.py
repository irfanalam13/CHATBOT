"""Chunking strategies: fixed, recursive, semantic, parent_child, hierarchical, adaptive."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.core.config import settings


@dataclass
class Chunk:
    content: str
    index: int
    page_number: int | None = None
    parent_index: int | None = None
    metadata: dict = field(default_factory=dict)


def _approx_tokens(text: str) -> int:
    # ~4 chars/token heuristic; good enough for sizing without a tokenizer call.
    return max(1, len(text) // 4)


def _fixed(text: str, size: int, overlap: int) -> list[str]:
    step = max(1, size - overlap)
    return [text[i : i + size] for i in range(0, len(text), step) if text[i : i + size].strip()]


def _recursive(text: str, size: int, overlap: int) -> list[str]:
    """Split on progressively finer separators, then merge to target size."""
    separators = ["\n\n", "\n", ". ", " "]

    def split(t: str, seps: list[str]) -> list[str]:
        if not seps or len(t) <= size:
            return [t]
        sep = seps[0]
        parts, buf, out = t.split(sep), "", []
        for p in parts:
            candidate = f"{buf}{sep}{p}" if buf else p
            if len(candidate) <= size:
                buf = candidate
            else:
                if buf:
                    out.append(buf)
                out.extend(split(p, seps[1:]) if len(p) > size else [p])
                buf = ""
        if buf:
            out.append(buf)
        return out

    raw = [c.strip() for c in split(text, separators) if c.strip()]
    # Re-stitch overlap.
    merged: list[str] = []
    for c in raw:
        if merged and overlap:
            tail = merged[-1][-overlap:]
            merged.append((tail + " " + c).strip() if len(c) < size else c)
        else:
            merged.append(c)
    return merged


def _semantic(text: str, size: int, overlap: int) -> list[str]:
    """Greedy sentence packing — keeps semantically whole sentences together."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks, buf = [], ""
    for s in sentences:
        if len(buf) + len(s) <= size:
            buf = f"{buf} {s}".strip()
        else:
            if buf:
                chunks.append(buf)
            buf = s
    if buf:
        chunks.append(buf)
    return chunks


def chunk_text(
    text: str,
    *,
    strategy: str | None = None,
    size: int | None = None,
    overlap: int | None = None,
    page_map: list[tuple[int, int]] | None = None,
) -> list[Chunk]:
    """Return Chunks. ``page_map`` maps char offset → page for page citations.

    Strategies:
      fixed        — fixed-width windows with overlap
      recursive    — separator-aware recursive split (default)
      semantic     — sentence-boundary packing
      parent_child — small child chunks linked to larger parent chunks
      hierarchical — multi-granularity (doc → section → chunk) flattened
      adaptive     — pick size based on document length
    """
    strategy = strategy or settings.DEFAULT_CHUNK_STRATEGY
    size = size or settings.CHUNK_SIZE
    overlap = overlap if overlap is not None else settings.CHUNK_OVERLAP

    if strategy == "adaptive":
        size = 400 if len(text) < 4000 else 800 if len(text) < 40000 else 1200
        strategy = "recursive"

    if strategy == "parent_child":
        return _parent_child(text, size, overlap)
    if strategy == "hierarchical":
        return _hierarchical(text, size, overlap)

    splitter = {"fixed": _fixed, "semantic": _semantic}.get(strategy, _recursive)
    pieces = splitter(text, size, overlap)
    return [
        Chunk(content=p, index=i, page_number=_page_for(text, p, page_map))
        for i, p in enumerate(pieces)
    ]


def _parent_child(text: str, size: int, overlap: int) -> list[Chunk]:
    parents = _recursive(text, size * 3, overlap)
    chunks: list[Chunk] = []
    idx = 0
    for p_i, parent in enumerate(parents):
        parent_idx = idx
        chunks.append(Chunk(content=parent, index=idx, metadata={"level": "parent"}))
        idx += 1
        for child in _recursive(parent, size, overlap):
            chunks.append(
                Chunk(content=child, index=idx, parent_index=parent_idx,
                      metadata={"level": "child"})
            )
            idx += 1
    return chunks


def _hierarchical(text: str, size: int, overlap: int) -> list[Chunk]:
    sections = [s for s in re.split(r"\n#{1,6}\s", text) if s.strip()]
    chunks: list[Chunk] = []
    idx = 0
    for sec in sections:
        for piece in _recursive(sec, size, overlap):
            chunks.append(Chunk(content=piece, index=idx, metadata={"level": "section"}))
            idx += 1
    return chunks or chunk_text(text, strategy="recursive", size=size, overlap=overlap)


def _page_for(text: str, piece: str, page_map: list[tuple[int, int]] | None) -> int | None:
    if not page_map:
        return None
    pos = text.find(piece[:50])
    if pos < 0:
        return None
    page = None
    for offset, p in page_map:
        if offset <= pos:
            page = p
        else:
            break
    return page
