"""Unit tests for the rule-based SectionDetector (10-K, 10-Q, transcript)."""

from __future__ import annotations

import pytest

from app.ingestion.section_detection import SectionDetector

DET = SectionDetector()


def _by_name(sections) -> dict[str, tuple[int, int, float]]:
    return {
        s.normalized_section_name: (s.start_page, s.end_page, s.confidence_score)
        for s in sections
    }


@pytest.mark.unit
def test_detects_10k_sections_and_skips_toc() -> None:
    pages = [
        (1, "Table of Contents\nItem 1A. Risk Factors .......... 12\nItem 7. MD&A .......... 30"),
        (2, "PART I\nItem 1. Business\nWe build robots and automation systems."),
        (3, "Item 1A. Risk Factors\nThe following risks could materially affect us."),
        (4, "These risks continue onto this page."),
        (5, "Item 7. Management's Discussion and Analysis\nRevenue rose 10%."),
        (6, "Item 8. Financial Statements\nConsolidated Balance Sheets follow."),
    ]
    result = _by_name(DET.detect(pages, report_type="10-K"))

    assert set(result) == {"Business Overview", "Risk Factors", "MD&A", "Financial Statements"}
    assert result["Risk Factors"][:2] == (3, 4)        # boundary runs to page before MD&A
    assert result["MD&A"][:2] == (5, 5)
    assert result["Risk Factors"][2] == 0.95           # SEC item confidence
    # The TOC page (1) must not create a section start.
    assert all(start >= 2 for start, _, _ in result.values())


@pytest.mark.unit
def test_detects_10q_part_aware_item_numbers() -> None:
    pages = [
        (1, "PART I - FINANCIAL INFORMATION\nItem 1. Financial Statements\nBalance sheets."),
        (2, "Item 2. Management's Discussion and Analysis\nResults of operations."),
        (3, "Item 3. Quantitative and Qualitative Disclosures About Market Risk\nDetails."),
        (4, "PART II - OTHER INFORMATION\nItem 1A. Risk Factors\nNo material changes."),
    ]
    result = _by_name(DET.detect(pages, report_type="10-Q"))

    # Item 2 is MD&A in a 10-Q (would be Properties in a 10-K) — part/type aware.
    assert result["MD&A"][0] == 2
    assert result["Financial Statements"][0] == 1
    assert result["Market Risk Disclosures"][0] == 3
    assert result["Risk Factors"][0] == 4              # Part II Item 1A


@pytest.mark.unit
def test_detects_transcript_sections() -> None:
    pages = [
        (1, "Operator\nGood morning and welcome to the call."),
        (2, "Prepared Remarks\nJohn Smith - Chief Executive Officer\nWe had a strong quarter."),
        (3, "Question-and-Answer Session\nFirst question from an analyst."),
        (4, "Closing Remarks\nThank you all for joining."),
    ]
    result = _by_name(DET.detect(pages, report_type="TRANSCRIPT"))

    assert "Operator Remarks" in result
    assert "Prepared Remarks" in result
    assert "Question & Answer" in result
    assert "Closing Remarks" in result
    assert "CEO Commentary" in result                  # detected within prepared remarks
    assert result["Operator Remarks"][2] == 0.9        # transcript-marker confidence
    assert result["CEO Commentary"][2] == 0.75         # pattern-tier confidence


@pytest.mark.unit
def test_confidence_tiers() -> None:
    # Exact alias, mixed case -> 0.85
    assert _by_name(DET.detect([(1, "Risk Factors\nbody")], "OTHER"))["Risk Factors"][2] == 0.85
    # Exact alias, uppercase -> bumped to 0.9
    assert _by_name(DET.detect([(1, "RISK FACTORS\nbody")], "OTHER"))["Risk Factors"][2] == 0.9
    # Pattern containment -> 0.75
    assert (
        _by_name(DET.detect([(1, "Summary of Risk Factors\nbody")], "OTHER"))["Risk Factors"][2]
        == 0.75
    )


@pytest.mark.unit
def test_fallback_when_nothing_detected() -> None:
    pages = [(1, "random unstructured prose"), (2, "more prose without headings")]
    sections = DET.detect(pages, report_type="OTHER")
    assert len(sections) == 1
    assert sections[0].normalized_section_name == "Uncategorized"
    assert sections[0].start_page == 1 and sections[0].end_page == 2
    assert sections[0].confidence_score == 0.3


@pytest.mark.unit
def test_empty_pages_returns_empty() -> None:
    assert DET.detect([], report_type="10-K") == []


@pytest.mark.unit
def test_section_content_spans_boundary_pages() -> None:
    pages = [
        (1, "Item 1A. Risk Factors\nRisk one."),
        (2, "Risk two continues here."),
        (3, "Item 8. Financial Statements\nNumbers."),
    ]
    sections = {s.normalized_section_name: s for s in DET.detect(pages, "10-K")}
    rf = sections["Risk Factors"]
    assert rf.start_page == 1 and rf.end_page == 2
    assert "Risk one." in rf.content and "Risk two" in rf.content
