"""Reranking service layer (Phase 6)."""

from __future__ import annotations

import time
from app.core.logging import get_logger
from app.rag.reranking.models import RerankResult
from app.rag.reranking.reranker import BGEReranker
from app.rag.reranking.validators import validate_rerank_inputs
from app.retrieval.search.retrieval_models import SearchResult

log = get_logger(__name__)


class RerankService:
    """Service to execute re-ranking on search results."""

    def __init__(self, *, reranker: BGEReranker | None = None) -> None:
        self.reranker = reranker or BGEReranker()

    def rerank(self, query: str, results: list[SearchResult], *, top_k: int) -> list[SearchResult]:
        validate_rerank_inputs(query, results)

        if not results:
            return []

        t0 = time.monotonic()
        texts = [r.chunk_text for r in results]

        # Compute cross-encoder scores
        scores = self.reranker.compute_scores(query, texts)

        reranked_results = []
        for i, res in enumerate(results):
            # Normalize cross-encoder score if it came from raw model (which can have wide bounds)
            raw_score = scores[i] if i < len(scores) else 0.0

            # Linearly combine vector search score (cosine similarity [0, 1]) and cross-encoder score
            # Let's say: combined = 0.3 * vector_score + 0.7 * cross_encoder_score (normalized or raw)
            # If cross-encoder is local fallback (Jaccard [0, 1]), combination is simple.
            # If cross-encoder is real (log-odds), sigmoid maps it to [0, 1].
            import math
            # If score is > 1.0 or < 0.0 (like raw log-odds), run sigmoid
            if raw_score > 1.0 or raw_score < 0.0:
                sig_score = 1.0 / (1.0 + math.exp(-raw_score))
            else:
                sig_score = raw_score

            combined_score = round(0.3 * res.score + 0.7 * sig_score, 6)

            # Copy result with updated score
            reranked_res = SearchResult(
                chunk_id=res.chunk_id,
                report_id=res.report_id,
                section_id=res.section_id,
                score=combined_score,
                chunk_text=res.chunk_text,
                metadata={
                    **(res.metadata or {}),
                    "original_vector_score": res.score,
                    "cross_encoder_score": round(sig_score, 6)
                }
            )
            reranked_results.append(reranked_res)

        # Sort descending by combined score
        reranked_results.sort(key=lambda r: r.score, reverse=True)

        # Truncate to top_k
        final_results = reranked_results[:top_k]

        t1 = time.monotonic()
        log.info(
            "rerank.completed",
            query=query,
            candidates=len(results),
            returned=len(final_results),
            duration_ms=round((t1 - t0) * 1000, 2)
        )

        return final_results
