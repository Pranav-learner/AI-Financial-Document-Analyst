"""Exceptions for Phase 9: Investment Memo Generation Engine."""

from __future__ import annotations


class MemoError(Exception):
    """Base exception for all memo generation errors."""
    pass


class MemoGenerationError(MemoError):
    """Raised when memo generation fails or the LLM returns an invalid format."""
    pass


class InvalidMemoPackageError(MemoError):
    """Raised when the compiled MemoPackage fails verification or contains insufficient data."""
    pass


class MemoValidationError(MemoError):
    """Raised when the generated memo fails post-generation validation checks."""
    pass
