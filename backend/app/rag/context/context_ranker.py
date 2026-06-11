"""Relevance and metadata ranking for context chunks."""

from __future__ import annotations

from app.retrieval.search.retrieval_models import SearchResult


class ContextRanker:
    """Prioritizes and ranks context chunks prior to context block serialization."""

    def sort_chunks(self, results: list[SearchResult]) -> list[SearchResult]:
        """Sort chunks.

        We prioritize:
        1. Higher score (relevance/cross-encoder ranking)
        2. Recency (fiscal year from metadata if available)
        """
        def get_sort_key(res: SearchResult) -> tuple[float, int]:
            score = float(res.score)
            year = 0
            if res.metadata:
                try:
                    year = int(res.metadata.get("fiscal_year") or res.metadata.get("year") or 0)
                except (ValueError, TypeError):
                    year = 0
            return (score, year)

        # Sort descending by score, then by year
        return sorted(results, key=get_sort_key, reverse=True)
