"""Vector-search exceptions (Phase 2B).

Domain errors for the retrieval path. The API layer maps these to HTTP via the
existing envelope; `SearchError` subclasses carry an HTTP status + machine code
so a bad query becomes a clean 4xx rather than a 500.
"""

from __future__ import annotations

from app.core.exceptions import AppError


class SearchError(AppError):
    """Base for vector-search failures."""

    status_code = 500
    code = "SEARCH_ERROR"


class EmptyQueryError(SearchError):
    status_code = 422
    code = "EMPTY_QUERY"


class QueryTooLongError(SearchError):
    status_code = 422
    code = "QUERY_TOO_LONG"


class InvalidTopKError(SearchError):
    status_code = 422
    code = "INVALID_TOP_K"


class QueryEmbeddingError(SearchError):
    """Failed to generate or validate the query embedding (e.g. wrong dimension)."""

    status_code = 502
    code = "QUERY_EMBEDDING_ERROR"
