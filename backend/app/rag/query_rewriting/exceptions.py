"""Query rewriting exceptions."""

from __future__ import annotations


class QueryRewriterError(Exception):
    """Base exception for query rewriting issues."""
    pass


class QueryClassifierError(QueryRewriterError):
    """Exception for query classification issues."""
    pass


class QueryValidationError(QueryRewriterError):
    """Exception for query validation failures."""
    pass
