"""Comparison data contracts (Phase 3B)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from decimal import Decimal


@dataclass(frozen=True)
class MetricPoint:
    """A single metric value at a fiscal period (the unit the engine compares)."""

    metric_id: str
    normalized_metric_name: str
    value: Decimal
    fiscal_year: int | None
    fiscal_quarter: int | None
    confidence: float = 1.0

    def period_key(self) -> tuple[str, int | None, int | None]:
        return (self.normalized_metric_name, self.fiscal_year, self.fiscal_quarter)


@dataclass
class ChangeResult:
    """Output of the deterministic growth calculation."""

    absolute_change: Decimal | None
    percentage_change: Decimal | None
    flags: list[str] = field(default_factory=list)


@dataclass
class ComparisonRow:
    """A built (pre-persistence) comparison."""

    metric_id: str
    company_id: str
    metric_name: str
    comparison_type: str
    current_period: str
    previous_period: str
    current_value: Decimal
    previous_value: Decimal
    absolute_change: Decimal | None
    percentage_change: Decimal | None
    flags: list[str] = field(default_factory=list)


@dataclass
class ComparisonStats:
    """Observability for a comparison run (task §13)."""

    current_metrics: int = 0
    comparisons_generated: int = 0
    missing_periods: int = 0
    validation_failures: int = 0
    calculation_errors: int = 0
    duration_seconds: float = 0.0

    @property
    def coverage(self) -> float:
        """Fraction of current metrics that produced ≥1 comparison."""
        return round(self._covered / self.current_metrics, 4) if self.current_metrics else 0.0

    _covered: int = 0

    def as_dict(self) -> dict:
        d = {k: v for k, v in asdict(self).items() if not k.startswith("_")}
        d["coverage"] = self.coverage
        return d


@dataclass
class ComparisonResult:
    rows: list[ComparisonRow]
    stats: ComparisonStats
