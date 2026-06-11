"""Query embedding pipeline (Phase 2B, task §3).

Turns a raw query string into a validated query vector using the SAME Gemini
model as Phase 2A (`gemini-embedding-001`), but with the `RETRIEVAL_QUERY` task
type. The returned vector MUST match the stored dimension (768) or search is
meaningless — so we validate before search and log every failure.
"""

from __future__ import annotations

import math

from app.core.config import settings
from app.core.logging import get_logger
from app.retrieval.embeddings.exceptions import EmbeddingError
from app.retrieval.embeddings.provider import Embedding, EmbeddingProvider
from app.retrieval.search.retrieval_models import QueryEmbeddingStats
from app.retrieval.search.search_exceptions import (
    EmptyQueryError,
    QueryEmbeddingError,
    QueryTooLongError,
)

log = get_logger(__name__)


class QueryEmbedder:
    """Generate + validate a query embedding."""

    def __init__(self, provider: EmbeddingProvider, *, expected_dim: int | None = None) -> None:
        self.provider = provider
        self.expected_dim = expected_dim or settings.embedding_dim

    def embed(self, query: str) -> tuple[Embedding, QueryEmbeddingStats]:
        text = (query or "").strip()
        if not text:
            log.warning("search.query_empty")
            raise EmptyQueryError("Query must not be empty")
        if len(text) > settings.search_max_query_chars:
            log.warning("search.query_too_long", length=len(text))
            raise QueryTooLongError(
                f"Query exceeds {settings.search_max_query_chars} characters",
                details={"length": len(text)},
            )

        try:
            vector = self.provider.embed_query(text)
        except EmbeddingError as exc:
            log.error("search.query_embedding_failed", error=str(exc))
            raise QueryEmbeddingError(f"Failed to embed query: {exc}") from exc

        if vector is None or len(vector) != self.expected_dim:
            got = None if vector is None else len(vector)
            log.error("search.query_dimension_mismatch", expected=self.expected_dim, got=got)
            raise QueryEmbeddingError(
                f"Query embedding dimension {got} != expected {self.expected_dim}"
            )

        norm = math.sqrt(sum(x * x for x in vector))
        stats = QueryEmbeddingStats(
            dimension=len(vector),
            norm=round(norm, 6),
            preview=[round(x, 6) for x in vector[:5]],
            model=self.provider.model_name,
            task_type=settings.embedding_query_task_type,
        )
        return vector, stats
