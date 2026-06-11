"""Comparison builder (Phase 3B).

Turns a matched (current, previous) `MetricPoint` pair into a `ComparisonRow` by
running the deterministic growth calculation and formatting the period labels.
"""

from __future__ import annotations

from app.financial.comparison.comparison_models import ComparisonRow, MetricPoint
from app.financial.comparison.growth_calculator import compute_changes
from app.financial.comparison.period_matcher import PeriodMatcher


def build_comparison(
    current: MetricPoint, previous: MetricPoint, comparison_type: str, company_id: str
) -> ComparisonRow:
    change = compute_changes(current.value, previous.value)
    return ComparisonRow(
        metric_id=current.metric_id,
        company_id=company_id,
        metric_name=current.normalized_metric_name,
        comparison_type=comparison_type,
        current_period=PeriodMatcher.format_period(current.fiscal_year, current.fiscal_quarter),
        previous_period=PeriodMatcher.format_period(previous.fiscal_year, previous.fiscal_quarter),
        current_value=current.value,
        previous_value=previous.value,
        absolute_change=change.absolute_change,
        percentage_change=change.percentage_change,
        flags=change.flags,
    )
