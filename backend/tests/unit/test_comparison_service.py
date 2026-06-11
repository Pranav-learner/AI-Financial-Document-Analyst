"""Unit tests for the comparison service + builder + validator (Phase 3B)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.financial.comparison import ComparisonService, MetricPoint
from app.financial.comparison.comparison_builder import build_comparison
from app.financial.comparison.comparison_validator import ComparisonValidator


def _p(name, value, year, quarter, *, mid=None, conf=0.9):
    return MetricPoint(
        metric_id=mid or f"{name}-{year}-{quarter}",
        normalized_metric_name=name, value=Decimal(str(value)),
        fiscal_year=year, fiscal_quarter=quarter, confidence=conf,
    )


@pytest.mark.unit
def test_yoy_annual_comparison() -> None:
    pts = [_p("REVENUE", 96700000000, 2024, None), _p("REVENUE", 81500000000, 2023, None)]
    res = ComparisonService().build_comparisons([pts[0]], pts, "c1")
    assert len(res.rows) == 1
    r = res.rows[0]
    assert r.comparison_type == "YOY"
    assert r.previous_period == "FY2023" and r.current_period == "FY2024"
    assert r.absolute_change == Decimal("15200000000")
    assert r.percentage_change == Decimal("18.65")


@pytest.mark.unit
def test_quarterly_yoy_and_qoq() -> None:
    pts = [
        _p("REVENUE", 27000000000, 2025, 2),
        _p("REVENUE", 25000000000, 2025, 1),
        _p("REVENUE", 24000000000, 2024, 2),
    ]
    res = ComparisonService().build_comparisons([pts[0]], pts, "c1")
    types = {r.comparison_type for r in res.rows}
    assert types == {"YOY", "QOQ"}
    qoq = next(r for r in res.rows if r.comparison_type == "QOQ")
    assert qoq.previous_period == "Q1 2025" and qoq.percentage_change == Decimal("8.00")


@pytest.mark.unit
def test_missing_previous_period_yields_nothing() -> None:
    pts = [_p("TOTAL_DEBT", 25000000000, 2024, None)]
    res = ComparisonService().build_comparisons(pts, pts, "c1")
    assert res.rows == []
    assert res.stats.missing_periods >= 1
    assert res.stats.coverage == 0.0


@pytest.mark.unit
def test_zero_previous_stores_null_percentage() -> None:
    pts = [_p("FREE_CASH_FLOW", 5000000000, 2024, None), _p("FREE_CASH_FLOW", 0, 2023, None)]
    res = ComparisonService().build_comparisons([pts[0]], pts, "c1")
    r = res.rows[0]
    assert r.absolute_change == Decimal("5000000000")
    assert r.percentage_change is None       # division by zero → stored as NULL


@pytest.mark.unit
def test_dedupe_keeps_highest_confidence() -> None:
    pts = [
        _p("REVENUE", 96700000000, 2024, None, mid="hi", conf=0.95),
        _p("REVENUE", 90000000000, 2024, None, mid="lo", conf=0.50),
        _p("REVENUE", 81500000000, 2023, None),
    ]
    res = ComparisonService().build_comparisons(
        [pts[0], pts[1]], pts, "c1"
    )
    assert len(res.rows) == 1                 # one logical revenue comparison
    assert res.rows[0].current_value == Decimal("96700000000")  # higher-confidence wins


@pytest.mark.unit
def test_coverage_and_stats() -> None:
    pts = [
        _p("REVENUE", 100, 2024, None), _p("REVENUE", 80, 2023, None),
        _p("EBITDA", 50, 2024, None),   # no prior EBITDA → no comparison
    ]
    res = ComparisonService().build_comparisons([pts[0], pts[2]], pts, "c1")
    assert res.stats.current_metrics == 2
    assert res.stats.comparisons_generated == 1
    assert res.stats.coverage == 0.5


@pytest.mark.unit
def test_validator_flags_duplicate() -> None:
    p_cur = _p("REVENUE", 100, 2024, None)
    p_prev = _p("REVENUE", 80, 2023, None)
    row = build_comparison(p_cur, p_prev, "YOY", "c1")
    v = ComparisonValidator()
    seen: set = set()
    assert v.validate(row, seen=seen).is_valid
    seen.add((row.metric_id, "YOY"))
    res = v.validate(row, seen=seen)
    assert not res.is_valid and "duplicate_comparison" in res.fatal
