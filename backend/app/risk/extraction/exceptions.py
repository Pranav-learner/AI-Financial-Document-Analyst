"""Risk-extraction exceptions (Phase 4)."""

from __future__ import annotations


class RiskExtractionError(Exception):
    """Base for risk-extraction failures."""


class RiskLLMError(RiskExtractionError):
    """LLM call failed or returned unusable payload."""

    retryable: bool = False


class RiskLLMTransientError(RiskLLMError):
    retryable = True


class RiskLLMResponseError(RiskLLMError):
    """Response was not valid JSON / did not match the schema. Not retryable."""

    retryable = False
