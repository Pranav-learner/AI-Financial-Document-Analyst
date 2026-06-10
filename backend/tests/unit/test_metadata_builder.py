"""Unit tests for chunk metadata building."""

from __future__ import annotations

import pytest

from app.ingestion.chunking.chunk_validation import REQUIRED_METADATA_KEYS
from app.ingestion.chunking.metadata_builder import (
    ReportContext,
    SectionContext,
    build_metadata,
)


@pytest.mark.unit
def test_build_metadata_has_all_required_keys_and_values() -> None:
    report = ReportContext(
        report_id="r1", report_type="10-Q", year=2026, quarter=1, company="ACME"
    )
    section = SectionContext(
        section_id="s1", section_name="Item 1A. Risk Factors",
        normalized_section_name="Risk Factors", start_page=12, end_page=20,
    )
    meta = build_metadata(report, section)

    assert set(meta.keys()) == REQUIRED_METADATA_KEYS
    assert meta["company"] == "ACME"
    assert meta["report_type"] == "10-Q"
    assert meta["quarter"] == 1
    assert meta["normalized_section_name"] == "Risk Factors"
    assert meta["start_page"] == 12 and meta["end_page"] == 20
    assert meta["report_id"] == "r1" and meta["section_id"] == "s1"


@pytest.mark.unit
def test_company_may_be_none() -> None:
    report = ReportContext(
        report_id="r1", report_type="OTHER", year=2026, quarter=None, company=None
    )
    section = SectionContext(
        section_id="s1", section_name="X", normalized_section_name="Uncategorized",
        start_page=1, end_page=1,
    )
    meta = build_metadata(report, section)
    assert meta["company"] is None
    assert meta["quarter"] is None
