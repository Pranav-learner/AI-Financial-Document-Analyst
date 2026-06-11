"""Unit tests for metric validators (Phase 3A)."""

from __future__ import annotations

from decimal import Decimal

import pytest
from app.financial.extraction.extraction_models import MetricCandidate
from app.financial.extraction.validators import MetricValidator


def _cand(**over):
    base = dict(
        normalized_metric_name="REVENUE", metric_name="Revenue", category="REVENUE",
        value=Decimal("96700000000"), currency="USD", unit="BILLION",
        fiscal_year=2024, fiscal_quarter=None, source_chunk_id="c1",
        source_text="Total revenue was $96.7 billion", method="RULE_BASED",
        raw_confidence=0.8,
    )
    base.update(over)
    return MetricCandidate(**base)


@pytest.mark.unit
def test_valid_metric_passes() -> None:
    assert MetricValidator().validate(_cand()).is_valid


@pytest.mark.unit
def test_unknown_currency_is_fatal() -> None:
    res = MetricValidator().validate(_cand(currency="ZZZ"))
    assert not res.is_valid and any("unknown_currency" in f for f in res.fatal)


@pytest.mark.unit
def test_unknown_unit_is_fatal() -> None:
    res = MetricValidator().validate(_cand(unit="ZILLION"))
    assert not res.is_valid and any("unknown_unit" in f for f in res.fatal)


@pytest.mark.unit
def test_bad_quarter_is_fatal() -> None:
    res = MetricValidator().validate(_cand(fiscal_quarter=7))
    assert not res.is_valid and any("bad_fiscal_quarter" in f for f in res.fatal)


@pytest.mark.unit
def test_bad_year_is_fatal() -> None:
    res = MetricValidator().validate(_cand(fiscal_year=1500))
    assert not res.is_valid


@pytest.mark.unit
def test_value_out_of_range_is_fatal() -> None:
    res = MetricValidator().validate(_cand(value=Decimal(10) ** 16))
    assert not res.is_valid and "value_out_of_range" in res.fatal


@pytest.mark.unit
def test_percent_out_of_range_is_fatal() -> None:
    res = MetricValidator().validate(
        _cand(normalized_metric_name="OPERATING_MARGIN", category="MARGINS",
              unit="PERCENT", currency=None, value=Decimal("50000"))
    )
    assert not res.is_valid and "percent_out_of_range" in res.fatal


@pytest.mark.unit
def test_negative_revenue_is_warning_not_fatal() -> None:
    res = MetricValidator().validate(_cand(value=Decimal("-100")))
    assert res.is_valid
    assert "unexpected_negative" in res.warnings


@pytest.mark.unit
def test_negative_net_income_is_fine() -> None:
    res = MetricValidator().validate(
        _cand(normalized_metric_name="NET_INCOME", category="PROFITABILITY", value=Decimal("-500"))
    )
    assert res.is_valid and not res.warnings
