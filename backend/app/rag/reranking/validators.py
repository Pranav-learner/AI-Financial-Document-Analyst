"""Rerank validators."""

from __future__ import annotations

from app.retrieval.search.search_exceptions import SearchError


def validate_rerank_inputs(query: str, results: list) -> None:
    """Ensure that query is non-empty and results is a valid list."""
    if not (query or "").strip():
        raise SearchError("Query cannot be empty for reranking")
    if not isinstance(results, list):
        raise SearchError("Reranking requires a list of candidate results")
