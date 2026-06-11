"""Unit tests for period matching (Phase 3B)."""

from __future__ import annotations

import pytest

from app.financial.comparison.period_matcher import PeriodMatcher


@pytest.mark.unit
def test_yoy_annual() -> None:
    assert PeriodMatcher.previous_period("YOY", 2024, None) == (2023, None)


@pytest.mark.unit
def test_yoy_quarterly_same_quarter() -> None:
    assert PeriodMatcher.previous_period("YOY", 2025, 1) == (2024, 1)


@pytest.mark.unit
def test_qoq_prior_quarter() -> None:
    assert PeriodMatcher.previous_period("QOQ", 2025, 2) == (2025, 1)


@pytest.mark.unit
def test_qoq_year_wrap() -> None:
    assert PeriodMatcher.previous_period("QOQ", 2025, 1) == (2024, 4)


@pytest.mark.unit
def test_qoq_on_annual_is_none() -> None:
    assert PeriodMatcher.previous_period("QOQ", 2024, None) is None


@pytest.mark.unit
def test_ytd_ttm_not_generated() -> None:
    assert PeriodMatcher.previous_period("YTD", 2024, 1) is None
    assert PeriodMatcher.previous_period("TTM", 2024, 1) is None


@pytest.mark.unit
def test_yoy_missing_year_is_none() -> None:
    assert PeriodMatcher.previous_period("YOY", None, None) is None


@pytest.mark.unit
def test_format_period() -> None:
    assert PeriodMatcher.format_period(2024, None) == "FY2024"
    assert PeriodMatcher.format_period(2025, 1) == "Q1 2025"
    assert PeriodMatcher.format_period(None, None) == "UNKNOWN"
