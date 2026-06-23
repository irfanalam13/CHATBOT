"""Chunking strategy tests."""
from __future__ import annotations

from app.rag.chunking import chunk_text

SAMPLE = ("Sentence one. Sentence two. " * 200).strip()


def test_recursive_produces_bounded_chunks():
    chunks = chunk_text(SAMPLE, strategy="recursive", size=200, overlap=20)
    assert len(chunks) > 1
    assert all(c.content for c in chunks)
    assert [c.index for c in chunks] == list(range(len(chunks)))


def test_fixed_chunking_window():
    chunks = chunk_text("x" * 1000, strategy="fixed", size=100, overlap=0)
    assert len(chunks) == 10


def test_semantic_keeps_sentences():
    chunks = chunk_text(SAMPLE, strategy="semantic", size=120, overlap=0)
    assert chunks
    # No chunk should split mid-word for plain sentences.
    assert all(not c.content.startswith(" ") for c in chunks)


def test_parent_child_links_children():
    chunks = chunk_text(SAMPLE, strategy="parent_child", size=150, overlap=10)
    assert any(c.parent_index is not None for c in chunks)
    assert any(c.metadata.get("level") == "parent" for c in chunks)


def test_adaptive_picks_strategy():
    chunks = chunk_text("short text", strategy="adaptive", size=800)
    assert chunks
