"""Deterministic metric validation (Phase 3A, task §7).

Every extracted value must pass these checks before persistence (ADR-007/ADR-017
— the LLM is never trusted blindly). FATAL issues drop the metric; WARNING issues
keep it but flag for review. All failures are logged.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from app.core.logging import get_logger
from app.financial.extraction.extraction_models import MetricCandidate

log = get_logger(__name__)

KNOWN_CURRENCIES = {"USD", "EUR", "GBP", "JPY", "CAD", "AUD", "CNY"}
KNOWN_UNITS = {"ABSOLUTE", "THOUSAND", "MILLION", "BILLION", "TRILLION", "PERCENT"}
KNOWN_CATEGORIES = {
    "REVENUE", "PROFITABILITY", "MARGINS", "CASH_FLOW",
    "DEBT", "CAPEX", "GUIDANCE", "OTHER",
}
# Metrics whose value is implausible if negative.
_NON_NEGATIVE = {"REVENUE", "TOTAL_DEBT", "CAPEX", "REVENUE_GUIDANCE"}
_MAX_ABS_CURRENCY = Decimal(10) ** 15   # sanity ceiling (~$1 quadrillion)


@dataclass
class ValidationResult:
    fatal: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.fatal


class MetricValidator:
    def validate(self, c: MetricCandidate) -> ValidationResult:
        result = ValidationResult()

        # numeric value
        if not isinstance(c.value, Decimal) or not c.value.is_finite():
            result.fatal.append("non_numeric_value")
        # malformed / required fields
        if not c.normalized_metric_name:
            result.fatal.append("missing_metric_name")
        if c.category not in KNOWN_CATEGORIES:
            result.fatal.append(f"unknown_category:{c.category}")
        if c.unit not in KNOWN_UNITS:
            result.fatal.append(f"unknown_unit:{c.unit}")
        # currency
        if c.currency is not None and c.currency not in KNOWN_CURRENCIES:
            result.fatal.append(f"unknown_currency:{c.currency}")
        # period references
        if c.fiscal_year is not None and not (1900 <= c.fiscal_year <= 2200):
            result.fatal.append(f"bad_fiscal_year:{c.fiscal_year}")
        if c.fiscal_quarter is not None and not (1 <= c.fiscal_quarter <= 4):
            result.fatal.append(f"bad_fiscal_quarter:{c.fiscal_quarter}")

        # outliers (only if value is usable)
        if isinstance(c.value, Decimal) and c.value.is_finite():
            if c.unit == "PERCENT":
                if abs(c.value) > Decimal(10000):
                    result.fatal.append("percent_out_of_range")
                elif abs(c.value) > Decimal(200):
                    result.warnings.append("percent_unusual")
            else:
                if abs(c.value) >= _MAX_ABS_CURRENCY:
                    result.fatal.append("value_out_of_range")
                if c.value < 0 and c.normalized_metric_name in _NON_NEGATIVE:
                    result.warnings.append("unexpected_negative")

        if not (c.source_text or "").strip():
            result.warnings.append("empty_source_text")

        if not result.is_valid:
            log.warning(
                "extraction.validation_failed",
                metric=c.normalized_metric_name,
                method=c.method,
                issues=result.fatal,
            )
        return result
