"""Deterministic risk validation (Phase 4).

Every extracted risk must pass these checks before persistence. FATAL issues
drop the risk; WARNING issues keep it but flag for review. All failures are logged.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.core.logging import get_logger

log = get_logger(__name__)

_VALID_CATEGORIES = {
    "SUPPLY_CHAIN", "REGULATORY", "MARKET", "COMPETITION", "TECHNOLOGY",
    "CYBERSECURITY", "OPERATIONAL", "LIQUIDITY", "GEOPOLITICAL", "LEGAL",
    "ENVIRONMENTAL", "REPUTATION", "MACROECONOMIC", "OTHER",
}
_VALID_SEVERITIES = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
_VALID_METHODS = {"RULE_BASED", "LLM_BASED", "HYBRID_VALIDATED"}


@dataclass
class RiskValidationResult:
    fatal: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.fatal


class RiskValidator:
    def validate(self, candidate) -> RiskValidationResult:
        result = RiskValidationResult()

        # Required fields
        if not (candidate.risk_name or "").strip():
            result.fatal.append("missing_risk_name")
        if not (candidate.normalized_risk_name or "").strip():
            result.fatal.append("missing_normalized_risk_name")
        if not (candidate.risk_description or "").strip():
            result.fatal.append("missing_risk_description")

        # Category validation
        if candidate.category not in _VALID_CATEGORIES:
            result.fatal.append(f"unknown_category:{candidate.category}")

        # Severity validation
        if candidate.severity not in _VALID_SEVERITIES:
            result.fatal.append(f"unknown_severity:{candidate.severity}")

        # Confidence range
        if not isinstance(candidate.raw_confidence, (int, float)):
            result.fatal.append("non_numeric_confidence")
        elif not (0.0 <= candidate.raw_confidence <= 1.0):
            result.warnings.append("confidence_out_of_range")

        # Source text
        if not (candidate.source_text or "").strip():
            result.warnings.append("empty_source_text")

        # Short description check
        if len((candidate.risk_description or "").strip()) < 10:
            result.warnings.append("very_short_description")

        if not result.is_valid:
            log.warning(
                "risk.validation_failed",
                risk=candidate.normalized_risk_name,
                method=candidate.method,
                issues=result.fatal,
            )
        return result
