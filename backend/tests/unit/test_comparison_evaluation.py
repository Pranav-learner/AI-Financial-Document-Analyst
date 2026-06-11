"""Unit tests for the comparison evaluation framework (Phase 3B)."""

from __future__ import annotations

import pytest

from app.financial.comparison.evaluation import ComparisonEvaluator, load_gold_scenarios


@pytest.mark.unit
def test_gold_scenarios_load() -> None:
    scenarios = load_gold_scenarios()
    assert len(scenarios) >= 5


@pytest.mark.unit
def test_engine_is_exactly_correct_on_gold() -> None:
    report = ComparisonEvaluator().evaluate(load_gold_scenarios())
    assert report.period_matching_accuracy == 1.0
    assert report.calculation_accuracy == 1.0
    assert report.comparison_coverage == 1.0
    assert report.validation_failure_rate == 0.0


@pytest.mark.unit
def test_report_serializes() -> None:
    d = ComparisonEvaluator().evaluate(load_gold_scenarios()).as_dict()
    assert {"period_matching_accuracy", "calculation_accuracy", "comparison_coverage"} <= set(d)
