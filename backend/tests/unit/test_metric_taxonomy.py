"""Unit tests for the metric taxonomy + alias resolution (Phase 3A)."""

from __future__ import annotations

import pytest
from app.financial.metrics.metric_aliases import find_aliases_in_text, resolve_alias
from app.financial.metrics.taxonomy import get_metric_taxonomy


@pytest.mark.unit
def test_taxonomy_loads_canonicals() -> None:
    tax = get_metric_taxonomy()
    canon = set(tax.canonicals())
    assert {"REVENUE", "NET_INCOME", "OPERATING_MARGIN", "CAPEX", "REVENUE_GUIDANCE"} <= canon


@pytest.mark.unit
@pytest.mark.parametrize(
    "surface,canonical",
    [
        ("Revenue", "REVENUE"),
        ("Net Sales", "REVENUE"),
        ("Total Revenue", "REVENUE"),
        ("Net Earnings", "NET_INCOME"),
        ("operating margin", "OPERATING_MARGIN"),
        ("capital expenditures", "CAPEX"),
    ],
)
def test_resolve_alias(surface, canonical) -> None:
    assert resolve_alias(surface) == canonical


@pytest.mark.unit
def test_unknown_alias_returns_none() -> None:
    assert resolve_alias("Quantum Flux Ratio") is None


@pytest.mark.unit
def test_value_kind() -> None:
    tax = get_metric_taxonomy()
    assert tax.value_kind("REVENUE") == "currency"
    assert tax.value_kind("OPERATING_MARGIN") == "percent"


@pytest.mark.unit
def test_find_aliases_longest_first() -> None:
    # "total net sales" should resolve as one REVENUE alias, not "sales" alone
    spans = find_aliases_in_text("Our total net sales grew")
    assert len(spans) == 1
    assert spans[0][0] == "REVENUE"
    assert spans[0][1].lower() == "total net sales"


@pytest.mark.unit
def test_find_aliases_ordered_by_position() -> None:
    text = "Total revenue rose; net income fell; operating margin held."
    spans = find_aliases_in_text(text)
    names = [s[0] for s in spans]
    assert names == ["REVENUE", "NET_INCOME", "OPERATING_MARGIN"]
