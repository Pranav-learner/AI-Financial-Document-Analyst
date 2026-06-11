"""Unit tests for deterministic growth calculations (Phase 3B)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.financial.comparison.growth_calculator import compute_changes


@pytest.mark.unit
def test_normal_growth() -> None:
    r = compute_changes(Decimal("96.7"), Decimal("81.5"))
    assert r.absolute_change == Decimal("15.2")
    assert r.percentage_change == Decimal("18.65")
    assert r.flags == []


@pytest.mark.unit
def test_exact_percentage_rounding() -> None:
    # 25000 vs 20000 → +25.00%
    r = compute_changes(Decimal("25000"), Decimal("20000"))
    assert r.percentage_change == Decimal("25.00")


@pytest.mark.unit
def test_decline() -> None:
    r = compute_changes(Decimal("80"), Decimal("100"))
    assert r.absolute_change == Decimal("-20")
    assert r.percentage_change == Decimal("-20.00")


@pytest.mark.unit
def test_zero_previous_division_by_zero() -> None:
    r = compute_changes(Decimal("10"), Decimal("0"))
    assert r.absolute_change == Decimal("10")
    assert r.percentage_change is None
    assert "division_by_zero" in r.flags


@pytest.mark.unit
def test_negative_base_flagged() -> None:
    r = compute_changes(Decimal("500"), Decimal("-1000"))
    assert r.absolute_change == Decimal("1500")
    assert r.percentage_change == Decimal("-150.00")
    assert "negative_base" in r.flags


@pytest.mark.unit
@pytest.mark.parametrize("cur,prev", [(None, Decimal("1")), (Decimal("1"), None), (None, None)])
def test_missing_values(cur, prev) -> None:
    r = compute_changes(cur, prev)
    assert r.absolute_change is None and r.percentage_change is None
    assert "missing_value" in r.flags
