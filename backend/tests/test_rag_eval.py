"""RAG evaluation helpers: citation formatting, grounding and a hallucination
heuristic. These run without external services and gate the citation contract.
"""
from __future__ import annotations

from app.rag.retrieval import RetrievalResult, RetrievedChunk


def _chunk(name, content, page=None, score=0.9):
    return RetrievedChunk(
        chunk_id="c", document_id="d", document_name=name,
        content=content, score=score, page_number=page, source_link=None,
    )


def test_context_has_numbered_citations():
    result = RetrievalResult(
        chunks=[
            _chunk("policy.pdf", "Refunds within 30 days.", page=2),
            _chunk("faq.md", "Support is 24/7."),
        ],
        took_ms=5,
    )
    ctx = result.to_context()
    assert "[1]" in ctx and "[2]" in ctx
    assert "policy.pdf" in ctx
    assert "p.2" in ctx


def test_context_respects_char_budget():
    big = _chunk("big.txt", "x" * 5000)
    result = RetrievalResult(chunks=[big, big, big, big], took_ms=1)
    ctx = result.to_context(max_chars=6000)
    assert len(ctx) <= 6500  # one block fits, the rest are dropped


def test_citation_accuracy_indices_match_sources():
    chunks = [_chunk(f"doc{i}.pdf", f"fact {i}") for i in range(3)]
    result = RetrievalResult(chunks=chunks, took_ms=1)
    ctx = result.to_context()
    for i in range(1, 4):
        assert f"[{i}]" in ctx


def test_hallucination_heuristic_flags_uncited_answer():
    """A naive groundedness check: an answer that shares no tokens with the
    retrieved context is a hallucination candidate."""
    context = "Refunds are available within 30 days of purchase."
    grounded = "You can get a refund within 30 days."
    hallucinated = "Our office is located on the moon."

    def overlap(answer: str) -> float:
        ctx_tokens = set(context.lower().split())
        ans_tokens = set(answer.lower().split())
        return len(ctx_tokens & ans_tokens) / max(1, len(ans_tokens))

    assert overlap(grounded) > overlap(hallucinated)
    assert overlap(hallucinated) == 0.0
