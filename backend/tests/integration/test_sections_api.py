"""Integration tests for Phase 1B: end-to-end sectioning + sections APIs."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.enums import ReportStatus
from app.models.report import Report
from app.models.report_section import ReportSection
from app.tasks.ingestion import detect_sections, process_report

PREFIX = settings.api_v1_prefix


async def _upload(client: AsyncClient, data: bytes, *, report_type: str, year: str) -> str:
    resp = await client.post(
        f"{PREFIX}/reports/upload",
        files={"file": ("f.pdf", data, "application/pdf")},
        data={"report_type": report_type, "year": year},
    )
    assert resp.status_code == 202, resp.text
    return resp.json()["report_id"]


@pytest.mark.integration
async def test_full_pipeline_10k_sections(api_client: AsyncClient, tenk_pdf_bytes: bytes) -> None:
    report_id = await _upload(api_client, tenk_pdf_bytes, report_type="10-K", year="2025")

    # Run the chained tasks directly (delays are stubbed in the fixture).
    assert process_report(report_id)["status"] == "PROCESSED"
    result = detect_sections(report_id)
    assert result["status"] == "SECTIONED"
    assert result["sections"] >= 3

    # Report status reflects sectioning.
    detail = (await api_client.get(f"{PREFIX}/reports/{report_id}")).json()
    assert detail["status"] == "SECTIONED"

    # List sections (no content) — normalized names present.
    listing = (await api_client.get(f"{PREFIX}/reports/{report_id}/sections")).json()
    names = {s["normalized_section_name"] for s in listing["items"]}
    assert {"Risk Factors", "MD&A", "Financial Statements"} <= names
    assert listing["count"] == len(listing["items"])

    # Section map (boundaries, no content).
    section_map = (await api_client.get(f"{PREFIX}/reports/{report_id}/section-map")).json()
    assert all("start_page" in s and "end_page" in s for s in section_map["sections"])

    # Section detail (with content).
    section_id = listing["items"][0]["id"]
    detail_section = (
        await api_client.get(f"{PREFIX}/reports/{report_id}/sections/{section_id}")
    ).json()
    assert "content" in detail_section
    assert 0.0 <= detail_section["confidence_score"] <= 1.0


@pytest.mark.integration
def test_detect_sections_missing_pages_marks_failed(sync_session: Session) -> None:
    report = Report(
        report_type="10-K", year=2025, original_filename="x.pdf",
        storage_path="reports/2026/06/none.pdf", status=ReportStatus.UPLOADED,
    )
    sync_session.add(report)
    sync_session.commit()

    result = detect_sections(str(report.id))
    assert result["status"] == "FAILED"
    sync_session.refresh(report)
    assert report.status == ReportStatus.FAILED
    assert report.error_message is not None


@pytest.mark.integration
def test_detect_sections_unknown_id_is_noop() -> None:
    assert detect_sections("00000000-0000-0000-0000-000000000000")["status"] == "MISSING"


@pytest.mark.integration
async def test_sections_404_for_unknown_report(api_client: AsyncClient) -> None:
    resp = await api_client.get(f"{PREFIX}/reports/00000000-0000-0000-0000-000000000000/sections")
    assert resp.status_code == 404


@pytest.mark.integration
def test_detect_is_idempotent(sync_session: Session, tenk_pdf_bytes: bytes) -> None:
    from app.ingestion.storage import get_storage

    storage_path = get_storage().save(tenk_pdf_bytes, extension=".pdf")
    report = Report(
        report_type="10-K", year=2025, original_filename="x.pdf",
        storage_path=storage_path, status=ReportStatus.PROCESSED, total_pages=4,
    )
    sync_session.add(report)
    sync_session.commit()
    # Insert pages so the task can section them.
    from app.models.report_page import ReportPage

    doc_pages = [
        "PART I\nItem 1. Business\nWe build robots.",
        "Item 1A. Risk Factors\nRisks.",
        "Item 7. Management's Discussion and Analysis\nRevenue.",
        "Item 8. Financial Statements\nNumbers.",
    ]
    sync_session.add_all(
        [ReportPage(report_id=report.id, page_number=i + 1, page_text=t)
         for i, t in enumerate(doc_pages)]
    )
    sync_session.commit()

    detect_sections(str(report.id))
    first = sync_session.query(ReportSection).filter(ReportSection.report_id == report.id).count()
    detect_sections(str(report.id))
    second = sync_session.query(ReportSection).filter(ReportSection.report_id == report.id).count()
    assert first == second  # re-running rebuilds, does not duplicate
