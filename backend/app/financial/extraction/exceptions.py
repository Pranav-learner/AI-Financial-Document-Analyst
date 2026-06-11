"""Financial-extraction exceptions (Phase 3A)."""

from __future__ import annotations


class ExtractionError(Exception):
    """Base for metric-extraction failures."""


class LLMExtractionError(ExtractionError):
    """LLM call failed or returned an unusable payload."""

    retryable: bool = False


class LLMTransientError(LLMExtractionError):
    retryable = True


class LLMResponseError(LLMExtractionError):
    """Response was not valid JSON / did not match the schema. Not retryable."""

    retryable = False


class ExtractionConfigError(ExtractionError):
    """Misconfiguration (e.g. missing taxonomy)."""
