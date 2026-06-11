"""Vector search service (Phase 2B, task §4).

Orchestrates the retrieval-only path:

    query → validate → generate query embedding → vector search → top-K results

No LLM reasoning, no generation, no post-processing, no filtering, no re-ranking.
The embedding provider call is synchronous (Gemini SDK), so it is run in a
threadpool to avoid blocking the async event loop. Latency is measured per stage
for observability (task §10).
"""

from __future__ import annotations

import time

from fastapi.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.retrieval.embeddings.gemini_provider import GeminiEmbeddingProvider
from app.retrieval.embeddings.provider import EmbeddingProvider
from app.retrieval.search.query_embedding import QueryEmbedder
from app.retrieval.search.retrieval_models import (
    QueryEmbeddingStats,
    SearchOutcome,
    SearchTimings,
)
from app.retrieval.search.search_exceptions import InvalidTopKError
from app.retrieval.search.vector_search import VectorSearch

log = get_logger(__name__)


class VectorSearchService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        provider: EmbeddingProvider | None = None,
        query_embedder: QueryEmbedder | None = None,
    ) -> None:
        self.session = session
        if query_embedder is not None:
            self.query_embedder = query_embedder
        else:
            provider = provider or GeminiEmbeddingProvider.from_settings()
            self.query_embedder = QueryEmbedder(provider)
        self.vector_search = VectorSearch(session)

    def _resolve_top_k(self, top_k: int | None) -> int:
        k = settings.search_default_top_k if top_k is None else top_k
        if k < settings.search_min_top_k or k > settings.search_max_top_k:
            raise InvalidTopKError(
                f"top_k must be between {settings.search_min_top_k} and "
                f"{settings.search_max_top_k}",
                details={"top_k": k},
            )
        return k

    async def run(
        self, query: str, *, top_k: int | None = None
    ) -> tuple[SearchOutcome, QueryEmbeddingStats]:
        """Execute a search; returns the outcome and the query-embedding stats."""
        k = self._resolve_top_k(top_k)

        t0 = time.monotonic()
        try:
            vector, stats = await run_in_threadpool(self.query_embedder.embed, query)
            t1 = time.monotonic()
            results = await self.vector_search.search(vector, top_k=k)
            t2 = time.monotonic()
        except Exception as exc:  # noqa: BLE001 - log + re-raise for the API envelope
            log.error("search.error", error=f"{type(exc).__name__}: {exc}")
            raise

        timings = SearchTimings(
            embedding_ms=round((t1 - t0) * 1000, 2),
            vector_search_ms=round((t2 - t1) * 1000, 2),
            total_ms=round((t2 - t0) * 1000, 2),
        )
        log.info(
            "search.complete",
            top_k=k,
            returned=len(results),
            top_score=results[0].score if results else None,
            **timings.as_dict(),
        )
        return (
            SearchOutcome(
                results=results, timings=timings, requested_top_k=k, returned=len(results)
            ),
            stats,
        )

    async def search(self, query: str, *, top_k: int | None = None) -> SearchOutcome:
        outcome, _ = await self.run(query, top_k=top_k)
        return outcome
