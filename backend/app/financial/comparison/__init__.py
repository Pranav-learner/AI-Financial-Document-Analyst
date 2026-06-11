"""Deterministic period-comparison engine (Phase 3B).

Computes YoY/QoQ deltas over stored `financial_metrics` values using deterministic
formulas — never an LLM (ADR-007/ADR-018). Period matching, growth calculation,
validation, and storage only — no trends, narratives, insights, or recommendations.

    from app.financial.comparison import (
        ComparisonService, MetricPoint, PeriodMatcher, compute_changes,
    )
"""

from app.financial.comparison.comparison_builder import build_comparison
from app.financial.comparison.comparison_models import (
    ChangeResult,
    ComparisonResult,
    ComparisonRow,
    ComparisonStats,
    MetricPoint,
)
from app.financial.comparison.comparison_service import ComparisonService
from app.financial.comparison.comparison_validator import ComparisonValidator, ValidationResult
from app.financial.comparison.exceptions import (
    CalculationError,
    ComparisonError,
    InvalidPeriodError,
)
from app.financial.comparison.growth_calculator import compute_changes
from app.financial.comparison.period_matcher import PeriodMatcher

__all__ = [
    "ComparisonService",
    "ComparisonValidator",
    "ValidationResult",
    "MetricPoint",
    "ComparisonRow",
    "ComparisonResult",
    "ComparisonStats",
    "ChangeResult",
    "PeriodMatcher",
    "compute_changes",
    "build_comparison",
    "ComparisonError",
    "InvalidPeriodError",
    "CalculationError",
]
