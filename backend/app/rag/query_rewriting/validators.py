"""Query validation rules."""

from __future__ import annotations

from app.core.config import settings
from app.rag.query_rewriting.exceptions import QueryValidationError


def validate_query(query: str) -> str:
    """Validate query input constraints."""
    text = (query or "").strip()
    if not text:
        raise QueryValidationError("Query must not be empty")
    if len(text) > settings.search_max_query_chars:
        raise QueryValidationError(
            f"Query exceeds maximum length of {settings.search_max_query_chars} characters"
        )
    return text
