"""HyDE document validators."""

from __future__ import annotations

from app.rag.query_rewriting.exceptions import QueryValidationError


def validate_hyde_document(doc: str) -> str:
    """Validate that the generated hypothetical document is non-empty and valid."""
    cleaned = (doc or "").strip()
    if not cleaned:
        raise QueryValidationError("Generated hypothetical document must not be empty")
    return cleaned
