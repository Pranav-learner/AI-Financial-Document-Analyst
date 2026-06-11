"""Comparison validation (Phase 3B, task §7).

Validates a built `ComparisonRow` before persistence. FATAL → drop (logged);
WARNING → keep (a deterministic "can't compute %" outcome like division-by-zero
is a valid, stored comparison with a NULL percentage).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.core.logging import get_logger
from app.financial.comparison.comparison_models import ComparisonRow

log = get_logger(__name__)


@dataclass
class ValidationResult:
    fatal: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.fatal


class ComparisonValidator:
    def validate(
        self, row: ComparisonRow, *, seen: set[tuple[str, str]]
    ) -> ValidationResult:
        result = ValidationResult()

        # corrupt source metrics (non-finite values that slipped through)
        for label, v in (("current_value", row.current_value), ("previous_value", row.previous_value)):
            if v is None or not v.is_finite():
                result.fatal.append(f"corrupt_source:{label}")

        # impossible result
        if "non_finite" in row.flags:
            result.fatal.append("non_finite_result")
        if row.absolute_change is not None and not row.absolute_change.is_finite():
            result.fatal.append("non_finite_absolute")

        # duplicate comparison (same current metric + type already produced)
        key = (row.metric_id, row.comparison_type)
        if key in seen:
            result.fatal.append("duplicate_comparison")

        # non-fatal, deterministic outcomes
        if "division_by_zero" in row.flags:
            result.warnings.append("division_by_zero")
        if "negative_base" in row.flags:
            result.warnings.append("negative_base")

        if not result.is_valid:
            log.warning(
                "comparison.validation_failed",
                metric=row.metric_name,
                type=row.comparison_type,
                issues=result.fatal,
            )
        return result
