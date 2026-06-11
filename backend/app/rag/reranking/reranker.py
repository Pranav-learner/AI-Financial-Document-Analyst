"""BAAI/bge-reranker-base cross-encoder wrapper (Phase 6)."""

from __future__ import annotations

import sys
from app.core.logging import get_logger
from app.retrieval.search.retrieval_models import SearchResult

log = get_logger(__name__)


class BGEReranker:
    """Wrapper around BAAI/bge-reranker-base cross-encoder with local fallback."""

    def __init__(self, *, model_name: str = "BAAI/bge-reranker-base", force_fallback: bool = False) -> None:
        self.model_name = model_name
        self.force_fallback = force_fallback
        self._reranker = None
        self._initialized = False

    def _initialize(self) -> None:
        if self._initialized:
            return

        self._initialized = True
        if self.force_fallback:
            log.info("reranker.init_fallback", reason="forced fallback mode")
            return

        # Try to import and load FlagEmbedding or sentence_transformers
        try:
            # Check if FlagEmbedding is installed
            import FlagEmbedding  # type: ignore[import-untyped]
            log.info("reranker.init_loading", model=self.model_name)
            self._reranker = FlagEmbedding.FlagReranker(self.model_name, use_fp16=True)
            log.info("reranker.init_success", model=self.model_name)
        except (ImportError, Exception) as exc:
            log.warning(
                "reranker.init_failed",
                model=self.model_name,
                error=f"{type(exc).__name__}: {exc}",
                msg="Falling back to Jaccard-overlap similarity scorer."
            )

    def compute_scores(self, query: str, texts: list[str]) -> list[float]:
        self._initialize()

        if not texts:
            return []

        # If real reranker is loaded, use it
        if self._reranker is not None:
            try:
                pairs = [[query, text] for text in texts]
                scores = self._reranker.compute_score(pairs)
                # Ensure we return float scores (FlagReranker can return list or float depending on input)
                if isinstance(scores, list):
                    return [float(s) for s in scores]
                return [float(scores)]
            except Exception as exc:
                log.error("reranker.execution_failed", error=str(exc))
                # Fall back to heuristic

        # Fallback calculation: word overlap + Jaccard similarity combined with length normalization
        query_words = set(query.lower().split())
        scores = []
        for text in texts:
            text_words = set(text.lower().split())
            intersection = query_words.intersection(text_words)
            union = query_words.union(text_words)
            jaccard = len(intersection) / len(union) if union else 0.0

            # Simple token matching bonus
            overlap = sum(1 for w in query_words if w in text_words)
            bonus = min(overlap * 0.05, 0.5)

            # Return a score between 0 and 1
            scores.append(round(min(1.0, jaccard + bonus), 4))

        return scores
