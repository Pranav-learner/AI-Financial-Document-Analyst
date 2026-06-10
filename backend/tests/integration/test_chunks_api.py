"""Integration tests for Phase 1C: end-to-end chunk generation + chunk APIs."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.enums import ReportStatus
from app.models.report import Report
from app.tasks.ingestion import detect_sections, generate_chunks, process_report

PREFIX = settings.api_v1_prefix


async def _upload(client: AsyncClient, data: bytes, *, report_type: str, year: str) -> str:
    resp = await client.post(
        f"{PREFIX}/reports/upload",
        files={"file": ("f.pdf", data, "application/pdf")},
        data={"report_type": report_type, "year": year, "ticker": "ACME"},
    )
    assert resp.status_code == 202, resp.text
    return resp.json()["report_id"]


@pytest.mark.integration
async def test_full_pipeline_to_chunks(api_client: AsyncClient, tenk_pdf_bytes: bytes) -> None:
    report_id = await _upload(api_client, tenk_pdf_bytes, report_type="10-K", year="2025")

    assert process_report(report_id)["status"] == "PROCESSED"
    assert detect_sections(report_id)["status"] == "SECTIONED"
    result = generate_chunks(report_id)
    assert result["status"] == "CHUNKED"
    assert result["chunks"] >= 1

    detail = (await api_client.get(f"{PREFIX}/reports/{report_id}")).json()
    assert detail["status"] == "CHUNKED"

    # List chunks (summaries).
    listing = (await api_client.get(f"{PREFIX}/reports/{report_id}/chunks")).json()
    assert listing["total"] == result["chunks"]
    assert listing["items"][0]["chunk_index"] == 0
    assert listing["items"][0]["normalized_section_name"] is not None

    # Chunk map.
    cmap = (await api_client.get(f"{PREFIX}/reports/{report_id}/chunk-map")).json()
    assert cmap["total_chunks"] == result["chunks"]

    # Chunk stats (inspection).
    stats = (await api_client.get(f"{PREFIX}/reports/{report_id}/chunk-stats")).json()
    assert stats["total_chunks"] == result["chunks"]
    assert stats["total_tokens"] > 0
    assert len(stats["sections"]) >= 1

    # Single chunk detail (with text + metadata).
    chunk_id = listing["items"][0]["id"]
    chunk = (await api_client.get(f"{PREFIX}/chunks/{chunk_id}")).json()
    assert chunk["chunk_text"]
    assert chunk["token_count"] > 0
    assert chunk["metadata"]["company"] == "ACME"
    assert chunk["metadata"]["report_id"] == report_id
    assert "normalized_section_name" in chunk["metadata"]
    # Phase 1C must NOT expose any embedding/vector field.
    assert "embedding" not in chunk and "vector" not in chunk


@pytest.mark.integration
def test_generate_chunks_without_sections_marks_failed(sync_session: Session) -> None:
    report = Report(
        report_type="10-K", year=2025, original_filename="x.pdf",
        storage_path="reports/2026/06/none.pdf", status=ReportStatus.PROCESSED,
    )
    sync_session.add(report)
    sync_session.commit()

    result = generate_chunks(str(report.id))
    assert result["status"] == "FAILED"
    sync_session.refresh(report)
    assert report.status == ReportStatus.FAILED
    assert report.error_message is not None


@pytest.mark.integration
def test_generate_chunks_unknown_id_is_noop() -> None:
    assert generate_chunks("00000000-0000-0000-0000-000000000000")["status"] == "MISSING"


@pytest.mark.integration
async def test_chunks_404_for_unknown_report(api_client: AsyncClient) -> None:
    resp = await api_client.get(f"{PREFIX}/reports/00000000-0000-0000-0000-000000000000/chunks")
    assert resp.status_code == 404


@pytest.mark.integration
def test_chunking_is_idempotent(sync_session: Session, tenk_pdf_bytes: bytes) -> None:
    from app.ingestion.storage import get_storage
    from app.models.document_chunk import DocumentChunk
    from app.models.report_page import ReportPage
    from app.models.report_section import ReportSection

    storage_path = get_storage().save(tenk_pdf_bytes, extension=".pdf")
    report = Report(
        report_type="10-K", year=2025, original_filename="x.pdf",
        storage_path=storage_path, status=ReportStatus.SECTIONED, total_pages=1,
    )
    sync_session.add(report)
    sync_session.commit()
    sync_session.add(ReportPage(report_id=report.id, page_number=1, page_text="x"))
    sync_session.add(
        ReportSection(
            report_id=report.id, section_name="Risk Factors",
            normalized_section_name="Risk Factors", start_page=1, end_page=1,
            content="Risk paragraph. " * 200, confidence_score=0.95,
        )
    )
    sync_session.commit()

    generate_chunks(str(report.id))
    first = sync_session.query(DocumentChunk).filter(DocumentChunk.report_id == report.id).count()
    generate_chunks(str(report.id))
    second = sync_session.query(DocumentChunk).filter(DocumentChunk.report_id == report.id).count()
    assert first == second and first > 0
