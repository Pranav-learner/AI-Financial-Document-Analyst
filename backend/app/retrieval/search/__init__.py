"""Vector search foundation (Phase 2B).

Retrieval ONLY: query → query embedding → pgvector cosine KNN → top-K chunks.
No metadata filtering, no hybrid retrieval, no re-ranking, no LLM/RAG (later phases).

Public surface:

    from app.retrieval.search import (
        VectorSearchService,
        VectorSearch,
        QueryEmbedder,
        SearchResult,
    )
"""

from app.retrieval.search.query_embedding import QueryEmbedder
from app.retrieval.search.retrieval_models import (
    QueryEmbeddingStats,
    SearchOutcome,
    SearchResult,
    SearchTimings,
)
from app.retrieval.search.search_exceptions import (
    EmptyQueryError,
    InvalidTopKError,
    QueryEmbeddingError,
    QueryTooLongError,
    SearchError,
)
from app.retrieval.search.search_service import VectorSearchService
from app.retrieval.search.vector_search import VectorSearch

__all__ = [
    "VectorSearchService",
    "VectorSearch",
    "QueryEmbedder",
    "SearchResult",
    "SearchOutcome",
    "SearchTimings",
    "QueryEmbeddingStats",
    "SearchError",
    "EmptyQueryError",
    "QueryTooLongError",
    "InvalidTopKError",
    "QueryEmbeddingError",
]
