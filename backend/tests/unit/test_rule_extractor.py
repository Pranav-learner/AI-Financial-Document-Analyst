"""Unit tests for the rule-based metric extractor (Phase 3A)."""

from __future__ import annotations

from decimal import Decimal

import pytest
from app.financial.extraction.extraction_models import ChunkInput
from app.financial.extraction.rule_extractor import RuleBasedExtractor


def _chunk(text, section="Income Statement", year=2024):
    return ChunkInput(chunk_id="c1", text=text, normalized_section_name=section,
                      fiscal_year=year, fiscal_quarter=None)


@pytest.mark.unit
def test_extracts_revenue_currency() -> None:
    out = RuleBasedExtractor().extract([_chunk("Total revenue was $96.7 billion in fiscal 2024.")])
    rev = next(c for c in out if c.normalized_metric_name == "REVENUE")
    assert rev.value == Decimal("96700000000.0")
    assert rev.currency == "USD" and rev.unit == "BILLION"
    assert rev.fiscal_year == 2024
    assert rev.method == "RULE_BASED"
    assert rev.section_match is True
    assert rev.source_chunk_id == "c1"


@pytest.mark.unit
def test_extracts_percent_for_margin() -> None:
    out = RuleBasedExtractor().extract(
        [_chunk("Operating margin was 28.5%.", section="MD&A")]
    )
    m = next(c for c in out if c.normalized_metric_name == "OPERATING_MARGIN")
    assert m.value == Decimal("28.5") and m.unit == "PERCENT"


@pytest.mark.unit
def test_currency_metric_skips_percent_value() -> None:
    # revenue is a currency metric; a bare percent nearby must not be bound to it
    out = RuleBasedExtractor().extract([_chunk("Revenue grew 10% to $96.7 billion.")])
    rev = next(c for c in out if c.normalized_metric_name == "REVENUE")
    assert rev.unit == "BILLION"  # picked the $ value, not the 10%


@pytest.mark.unit
def test_section_awareness_affects_confidence() -> None:
    in_section = RuleBasedExtractor().extract(
        [_chunk("Total revenue was $96.7 billion.", section="Income Statement")]
    )[0]
    off_section = RuleBasedExtractor().extract(
        [_chunk("Total revenue was $96.7 billion.", section="Legal Proceedings")]
    )[0]
    assert in_section.section_match is True
    assert off_section.section_match is False
    assert in_section.raw_confidence > off_section.raw_confidence


@pytest.mark.unit
def test_multiple_metrics_in_one_chunk() -> None:
    text = ("Total revenue was $96.7 billion. Net income was $5,123 million. "
            "Operating margin was 28.5%.")
    out = RuleBasedExtractor().extract([_chunk(text)])
    names = {c.normalized_metric_name for c in out}
    assert {"REVENUE", "NET_INCOME", "OPERATING_MARGIN"} <= names


@pytest.mark.unit
def test_no_value_no_candidate() -> None:
    out = RuleBasedExtractor().extract([_chunk("Revenue increased compared to last year.")])
    assert all(c.normalized_metric_name != "REVENUE" for c in out)
