"""Cross-encoder reranking with a graceful no-op fallback."""
from __future__ import annotations

from functools import lru_cache

from app.core.logging import get_logger
from app.rag.vectorstore import VectorHit

log = get_logger("rag.reranker")


@lru_cache(maxsize=1)
def _load_cross_encoder():
    try:
        from sentence_transformers import CrossEncoder

        return CrossEncoder("BAAI/bge-reranker-base")
    except Exception as e:  # model not available → fall back to identity rerank
        log.warning("reranker_unavailable", error=str(e))
        return None


def rerank(query: str, hits: list[VectorHit], top_n: int) -> list[VectorHit]:
    if not hits:
        return hits
    model = _load_cross_encoder()
    if model is None:
        return hits[:top_n]
    pairs = [(query, h.payload.get("content", "")) for h in hits]
    scores = model.predict(pairs)
    rescored = sorted(zip(hits, scores), key=lambda x: x[1], reverse=True)
    out: list[VectorHit] = []
    for hit, score in rescored[:top_n]:
        hit.score = float(score)
        out.append(hit)
    return out
