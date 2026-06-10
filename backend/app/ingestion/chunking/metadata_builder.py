"""Chunk metadata builder (Phase 1C).

Builds the structured metadata attached to every chunk. Denormalizing company /
period / section attributes onto the chunk is what makes future metadata-filtered
hybrid retrieval (Phase 6) cheap — without a join. No vectors here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ReportContext:
    """The report/company facts needed to stamp chunk metadata."""

    report_id: str
    report_type: str
    year: int
    quarter: int | None
    company: str | None  # ticker (preferred) or company name


@dataclass(frozen=True)
class SectionContext:
    section_id: str
    section_name: str
    normalized_section_name: str
    start_page: int
    end_page: int


def build_metadata(report: ReportContext, section: SectionContext) -> dict[str, Any]:
    """Assemble the canonical chunk metadata dict."""
    return {
        "company": report.company,
        "report_type": report.report_type,
        "year": report.year,
        "quarter": report.quarter,
        "section_name": section.section_name,
        "normalized_section_name": section.normalized_section_name,
        "start_page": section.start_page,
        "end_page": section.end_page,
        "report_id": report.report_id,
        "section_id": section.section_id,
    }
