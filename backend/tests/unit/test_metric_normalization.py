"""Unit tests for deterministic value normalization (Phase 3A)."""

from __future__ import annotations

from decimal import Decimal

import pytest
from app.financial.metrics.normalization import (
    find_values,
    normalize_currency,
    normalize_value,
    parse_period,
)


@pytest.mark.unit
@pytest.mark.parametrize(
    "text,value,currency,unit",
    [
        ("$96.7 billion", Decimal("96700000000.0"), "USD", "BILLION"),
        ("$96,700 million", Decimal("96700000000"), "USD", "MILLION"),
        ("28.5%", Decimal("28.5"), None, "PERCENT"),
        ("$1,284", Decimal("1284"), "USD", "ABSOLUTE"),
        ("$96.7B", Decimal("96700000000.0"), "USD", "BILLION"),
        ("96.7bn", Decimal("96700000000.0"), None, "BILLION"),
        ("USD 1.2 billion", Decimal("1200000000.0"), "USD", "BILLION"),
        ("operating margin was 28.5 percent", Decimal("28.5"), None, "PERCENT"),
    ],
)
def test_normalize_value(text, value, currency, unit) -> None:
    v = normalize_value(text)
    assert v is not None
    assert v.value == value
    assert v.currency == currency
    assert v.unit == unit


@pytest.mark.unit
def test_same_value_different_scale() -> None:
    a = normalize_value("$96.7 billion")
    b = normalize_value("$96,700 million")
    assert a.value == b.value == Decimal("96700000000")


@pytest.mark.unit
def test_negative_parentheses() -> None:
    v = normalize_value("(1,234)")
    assert v.value == Decimal("-1234")


@pytest.mark.unit
def test_no_value() -> None:
    assert normalize_value("no numbers here") is None


@pytest.mark.unit
def test_find_multiple_values() -> None:
    vs = find_values("revenue $96.7 billion and net income $5.1 billion")
    assert len(vs) == 2
    assert vs[0].value == Decimal("96700000000.0")


@pytest.mark.unit
def test_normalize_currency() -> None:
    assert normalize_currency("$") == "USD"
    assert normalize_currency("eur") == "EUR"
    assert normalize_currency(None) is None
    assert normalize_currency("ZZZ") is None


@pytest.mark.unit
def test_parse_period() -> None:
    assert parse_period("Q3 2024") == (2024, 3)
    assert parse_period("fiscal 2023") == (2023, None)
    assert parse_period(None) == (None, None)
