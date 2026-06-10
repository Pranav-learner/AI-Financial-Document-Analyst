"""Unit tests for section-detection pattern primitives."""

from __future__ import annotations

import pytest

from app.ingestion.section_detection.section_patterns import (
    clean_heading,
    is_mostly_uppercase,
    is_strong_heading,
    is_toc_line,
    match_sec_item,
)


@pytest.mark.unit
def test_match_sec_item_extracts_code_and_title() -> None:
    assert match_sec_item("Item 1A. Risk Factors") == ("1A", "Risk Factors")
    assert match_sec_item("ITEM 7 - Management's Discussion") == ("7", "Management's Discussion")
    assert match_sec_item("Item 8: Financial Statements") == ("8", "Financial Statements")


@pytest.mark.unit
def test_match_sec_item_rejects_non_items() -> None:
    assert match_sec_item("Risk Factors") is None
    assert match_sec_item("The item was discussed in detail.") is None


@pytest.mark.unit
def test_toc_line_detection() -> None:
    assert is_toc_line("Risk Factors .......... 12")
    assert is_toc_line("Management Discussion       30")
    assert not is_toc_line("Risk Factors")


@pytest.mark.unit
def test_clean_heading_strips_toc_and_enumeration() -> None:
    assert clean_heading("1A. Risk Factors .......... 12") == "Risk Factors"
    assert clean_heading("Item 7:") == "Item 7"
    assert clean_heading("RISK FACTORS") == "RISK FACTORS"


@pytest.mark.unit
def test_strong_heading_heuristic() -> None:
    assert is_strong_heading("Risk Factors")
    assert is_strong_heading("MANAGEMENT'S DISCUSSION AND ANALYSIS")
    assert not is_strong_heading(
        "These are the risks that could materially and adversely affect us this year."
    )


@pytest.mark.unit
def test_mostly_uppercase() -> None:
    assert is_mostly_uppercase("RISK FACTORS")
    assert not is_mostly_uppercase("Risk Factors")
