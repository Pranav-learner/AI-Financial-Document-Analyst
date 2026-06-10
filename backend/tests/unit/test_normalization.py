"""Unit tests for section-name normalization against the taxonomy."""

from __future__ import annotations

import pytest

from app.ingestion.section_detection.normalization import normalize_heading
from app.ingestion.section_detection.taxonomy import get_taxonomy

TAX = get_taxonomy()


@pytest.mark.unit
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Risk Factors", "Risk Factors"),
        ("Principal Risks", "Risk Factors"),
        ("Risk Considerations", "Risk Factors"),
        ("Management Discussion and Analysis", "MD&A"),
        ("MD&A", "MD&A"),
        ("Consolidated Statements of Cash Flows", "Cash Flow Statement"),
        ("Outlook", "Forward Guidance"),
    ],
)
def test_aliases_map_to_canonical(raw: str, expected: str) -> None:
    res = normalize_heading(raw, TAX)
    assert res.canonical == expected
    assert res.kind == "exact_alias"


@pytest.mark.unit
def test_case_insensitive_alias() -> None:
    assert normalize_heading("RISK FACTORS", TAX).canonical == "Risk Factors"


@pytest.mark.unit
def test_pattern_containment_match() -> None:
    res = normalize_heading("Summary of Risk Factors", TAX)
    assert res.canonical == "Risk Factors"
    assert res.kind == "pattern"


@pytest.mark.unit
def test_unknown_heading_returns_none() -> None:
    res = normalize_heading("Completely Unrelated Heading", TAX)
    assert res.canonical is None
    assert res.kind == "none"


@pytest.mark.unit
def test_empty_heading_returns_none() -> None:
    assert normalize_heading("   ", TAX).canonical is None
