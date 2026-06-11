"""Unit tests for the financial analytics engine (Phase 3C)."""

from __future__ import annotations

import uuid
from decimal import Decimal
import pytest

from app.models.financial_metric import FinancialMetric
from app.models.metric_comparison import MetricComparison
from app.financial.analytics.analytics_models import CalculatedRatio, GeneratedSignal
from app.financial.analytics.ratio_calculator import RatioCalculator
from app.financial.analytics.trend_classifier import TrendClassifier
from app.financial.analytics.signal_generator import SignalGenerator
from app.financial.analytics.analytics_validator import AnalyticsValidator
from app.financial.analytics.analytics_builder import AnalyticsBuilder


def _m(name: str, value: float, *, rid=None) -> FinancialMetric:
    return FinancialMetric(
        id=uuid.uuid4(),
        report_id=rid or uuid.uuid4(),
        metric_name=name,
        normalized_metric_name=name,
        metric_category="OTHER",
        value=Decimal(str(value)),
        unit="USD",
        confidence_score=1.0,
        extraction_method="RULE_BASED",
        source_text="",
    )


def _c(
    name: str,
    ctype: str,
    curr: float,
    prev: float,
    *,
    pct: float | None = None,
    abs_val: float | None = None,
    mid=None,
) -> MetricComparison:
    return MetricComparison(
        id=uuid.uuid4(),
        metric_id=mid or uuid.uuid4(),
        company_id=uuid.uuid4(),
        metric_name=name,
        comparison_type=ctype,
        current_period="2025-Q1",
        previous_period="2024-Q1",
        current_value=Decimal(str(curr)),
        previous_value=Decimal(str(prev)),
        absolute_change=Decimal(str(abs_val)) if abs_val is not None else None,
        percentage_change=Decimal(str(pct)) if pct is not None else None,
    )


@pytest.mark.unit
def test_ratio_calculator_basic() -> None:
    metrics = [
        _m("REVENUE", 1000.0),
        _m("GROSS_PROFIT", 600.0),
        _m("OPERATING_INCOME", 200.0),
        _m("NET_INCOME", 150.0),
        _m("TOTAL_DEBT", 200.0),
        _m("OPERATING_CASH_FLOW", 250.0),
    ]
    ratios = RatioCalculator().calculate_ratios(metrics)
    by_name = {r.name: r.value for r in ratios}
    
    assert len(ratios) == 5
    assert by_name["GROSS_MARGIN"] == Decimal("0.60")
    assert by_name["OPERATING_MARGIN"] == Decimal("0.20")
    assert by_name["NET_MARGIN"] == Decimal("0.15")
    assert by_name["DEBT_TO_REVENUE"] == Decimal("0.20")
    assert by_name["CASH_FLOW_MARGIN"] == Decimal("0.25")


@pytest.mark.unit
def test_ratio_calculator_fallback() -> None:
    # Test margins are used directly if profit is missing
    metrics = [
        _m("REVENUE", 1000.0),
        _m("GROSS_MARGIN", 0.65),
    ]
    ratios = RatioCalculator().calculate_ratios(metrics)
    assert len(ratios) == 1
    assert ratios[0].name == "GROSS_MARGIN"
    assert ratios[0].value == Decimal("0.65")


@pytest.mark.unit
def test_ratio_calculator_div_zero() -> None:
    # Revenue is zero, should not raise zero division error
    metrics = [
        _m("REVENUE", 0.0),
        _m("GROSS_PROFIT", 100.0),
    ]
    ratios = RatioCalculator().calculate_ratios(metrics)
    assert ratios == []


@pytest.mark.unit
def test_trend_classifier() -> None:
    tc = TrendClassifier()
    assert tc.classify_growth(Decimal("0.20")) == "STRONG_GROWTH"
    assert tc.classify_growth(Decimal("0.08")) == "MODERATE_GROWTH"
    assert tc.classify_growth(Decimal("0.02")) == "LOW_GROWTH"
    assert tc.classify_growth(Decimal("-0.05")) == "DECLINING"

    assert tc.classify_margin_change(Decimal("0.02")) == "MARGIN_EXPANSION"
    assert tc.classify_margin_change(Decimal("-0.01")) == "MARGIN_COMPRESSION"
    assert tc.classify_margin_change(Decimal("0.00")) == "MARGIN_UNCHANGED"

    assert tc.classify_debt_change(Decimal("-0.10")) == "DEBT_REDUCTION"
    assert tc.classify_debt_change(Decimal("0.05")) == "DEBT_INCREASE"
    assert tc.classify_debt_change(Decimal("0.00")) == "DEBT_UNCHANGED"


@pytest.mark.unit
def test_signal_generator_growth_and_margins() -> None:
    comparisons = [
        _c("REVENUE", "YOY", 1200.0, 1000.0, pct=0.20),
        _c("OPERATING_MARGIN", "YOY", 0.18, 0.15, abs_val=0.03),
        _c("TOTAL_DEBT", "YOY", 400.0, 500.0, pct=-0.20),
    ]
    metrics = [_m("REVENUE", 1200.0), _m("OPERATING_MARGIN", 0.18), _m("TOTAL_DEBT", 400.0)]
    
    signals = SignalGenerator().generate_signals(metrics, comparisons, [])
    by_code = {s.signal_code: s for s in signals}

    assert "REVENUE_GROWTH_YOY" in by_code
    assert by_code["REVENUE_GROWTH_YOY"].severity == "VERY_POSITIVE"

    assert "OPERATING_MARGIN_CHANGE_YOY" in by_code
    assert by_code["OPERATING_MARGIN_CHANGE_YOY"].severity == "POSITIVE"

    assert "DEBT_CHANGE_YOY" in by_code
    assert by_code["DEBT_CHANGE_YOY"].severity == "POSITIVE"  # Debt reduction is positive!


@pytest.mark.unit
def test_signal_generator_leverage() -> None:
    comparisons = [
        _c("TOTAL_DEBT", "YOY", 200.0, 300.0),
        _c("REVENUE", "YOY", 1000.0, 1000.0),
    ]
    metrics = [_m("TOTAL_DEBT", 200.0), _m("REVENUE", 1000.0)]

    signals = SignalGenerator().generate_signals(metrics, comparisons, [])
    by_code = {s.signal_code: s for s in signals}

    # Debt went from 300 to 200 on same revenue → Debt-to-Revenue ratio improved
    assert "LEVERAGE_IMPROVEMENT_YOY" in by_code
    assert by_code["LEVERAGE_IMPROVEMENT_YOY"].severity == "POSITIVE"


@pytest.mark.unit
def test_signal_generator_guidance() -> None:
    rid = uuid.uuid4()
    # Case A: Guidance above actual (no historical)
    metrics = [_m("REVENUE_GUIDANCE", 1500.0, rid=rid), _m("REVENUE", 1200.0, rid=rid)]
    signals = SignalGenerator().generate_signals(metrics, [], [])
    assert len(signals) == 1
    assert signals[0].signal_code == "GUIDANCE_ABOVE_ACTUAL"
    assert signals[0].severity == "POSITIVE"

    # Case B: Guidance compared to historical guidance
    hist_guidance = _m("REVENUE_GUIDANCE", 1400.0)  # different report_id
    signals_hist = SignalGenerator().generate_signals(metrics, [], [], [hist_guidance])
    by_code = {s.signal_code: s for s in signals_hist}
    assert "GUIDANCE_RAISED" in by_code
    assert by_code["GUIDANCE_RAISED"].severity == "VERY_POSITIVE"


@pytest.mark.unit
def test_analytics_validator() -> None:
    # 1. Test extreme ratio value
    ratios = [CalculatedRatio(name="GROSS_MARGIN", value=Decimal("25.0"))]
    valid_ratios, valid_signals, warnings = AnalyticsValidator().validate(ratios, [])
    assert len(valid_ratios) == 0
    assert len(warnings) == 1
    assert "Impossible ratio" in warnings[0]

    # 2. Test duplicate signals
    signals = [
        GeneratedSignal(
            signal_type="GROWTH",
            signal_code="REVENUE_GROWTH_YOY",
            metric_name="REVENUE",
            value=Decimal("0.20"),
            classification="STRONG_GROWTH",
            severity="VERY_POSITIVE",
        ),
        GeneratedSignal(
            signal_type="GROWTH",
            signal_code="REVENUE_GROWTH_YOY",
            metric_name="REVENUE",
            value=Decimal("0.20"),
            classification="STRONG_GROWTH",
            severity="VERY_POSITIVE",
        ),
    ]
    valid_ratios, valid_signals, warnings = AnalyticsValidator().validate([], signals)
    assert len(valid_signals) == 1
    assert len(warnings) == 1
    assert "Duplicate signal" in warnings[0]


@pytest.mark.unit
def test_analytics_builder() -> None:
    metrics = [_m("REVENUE", 1000.0), _m("GROSS_PROFIT", 600.0)]
    comparisons = [_c("REVENUE", "YOY", 1000.0, 800.0, pct=0.25)]
    
    rows, warnings = AnalyticsBuilder().build_analytics(
        company_id=uuid.uuid4(),
        report_id=uuid.uuid4(),
        metrics=metrics,
        comparisons=comparisons,
    )
    assert len(rows) == 2  # 1 ratio (GROSS_MARGIN) + 1 signal (REVENUE_GROWTH_YOY)
    assert any(r["signal_code"] == "GROSS_MARGIN" for r in rows)
    assert any(r["signal_code"] == "REVENUE_GROWTH_YOY" for r in rows)
