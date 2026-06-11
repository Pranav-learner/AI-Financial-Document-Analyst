"""Integration tests for Phase 9 Investment Memo API and Celery Tasks."""

from __future__ import annotations

import json
import uuid
from decimal import Decimal
import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.config import settings
from app.models.company import Company
from app.models.report import Report
from app.models.enums import ReportStatus, MemoStatus, MemoType
from app.models.financial_metric import FinancialMetric
from app.models.management_tone import ManagementTone
from app.models.risk_factor import RiskFactor
from app.models.document_chunk import DocumentChunk
from app.models.memo import InvestmentMemo, MemoSection
from app.tasks.memo import generate_memo_task

PREFIX = settings.api_v1_prefix


def _seed_memo_data(session: Session) -> tuple[Company, Report]:
    c = Company(name="Tesla Inc", ticker="TSLA")
    session.add(c)
    session.commit()

    r = Report(
        company_id=c.id,
        report_type="10-K",
        year=2025,
        original_filename="tsla_2025.pdf",
        storage_path="reports/2026/06/TSLA_2025.pdf",
        status=ReportStatus.PROCESSED,
        total_pages=15,
    )
    session.add(r)
    session.commit()

    # Seed chunks
    ch1 = DocumentChunk(
        report_id=r.id,
        start_page=1,
        end_page=1,
        chunk_index=0,
        chunk_text="Tesla reported record automotive revenues in fiscal year 2025.",
        chunk_metadata={"section_name": "Overview"},
        token_count=10,
    )
    ch2 = DocumentChunk(
        report_id=r.id,
        start_page=12,
        end_page=12,
        chunk_index=1,
        chunk_text="Supply chain vulnerabilities in lithium supply could pose risks.",
        chunk_metadata={"section_name": "Risk Factors"},
        token_count=10,
    )
    session.add_all([ch1, ch2])
    session.commit()

    # Seed Financial Metrics
    session.add(
        FinancialMetric(
            report_id=r.id,
            source_chunk_id=ch1.id,
            metric_name="AUTOMOTIVE_REVENUE",
            normalized_metric_name="AUTOMOTIVE_REVENUE",
            metric_category="REVENUE",
            value=Decimal("95000.0"),
            currency="USD",
            unit="MILLION",
            fiscal_year=2025,
            confidence_score=Decimal("1.0"),
            extraction_method="RULE_BASED",
            source_text="95 billion in automotive revenue",
        )
    )

    session.add(
        RiskFactor(
            company_id=c.id,
            report_id=r.id,
            source_chunk_id=ch2.id,
            risk_name="lithium supply chain risk",
            normalized_risk_name="lithium_supply_chain_risk",
            risk_description="lithium supply constraints",
            category="SUPPLY_CHAIN",
            severity="HIGH",
            confidence_score=Decimal("0.95"),
            extraction_method="RULE_BASED",
            source_text="lithium supply",
        )
    )

    # Seed Management Tone
    session.add(
        ManagementTone(
            company_id=c.id,
            report_id=r.id,
            source_chunk_id=ch1.id,
            source_type="MDA",
            sentiment="POSITIVE",
            confidence_level="CONFIDENT",
            hedging_score=Decimal("0.15"),
            positive_score=Decimal("0.85"),
            negative_score=Decimal("0.05"),
            confidence_score=Decimal("0.9"),
            extraction_method="RULE_BASED",
            source_text="record revenues",
        )
    )

    session.commit()
    return c, r


@pytest.mark.integration
async def test_generate_memo_endpoint_and_task_execution(
    api_client: AsyncClient,
    sync_session: Session,
) -> None:
    # 1. Seed
    company, report = _seed_memo_data(sync_session)

    # 2. Trigger via API
    payload = {
        "company_id": str(company.id),
        "report_id": str(report.id),
        "memo_type": "SINGLE_COMPANY",
        "title": "TSLA 2025 Analysis",
    }
    
    resp = await api_client.post(f"{PREFIX}/memos", json=payload)
    assert resp.status_code == 202, resp.text
    data = resp.json()
    assert "memo_id" in data
    memo_id_str = data["memo_id"]
    memo_id = uuid.UUID(memo_id_str)

    # Verify memo is in PENDING state in DB
    sync_session.expire_all()
    memo = sync_session.scalar(select(InvestmentMemo).where(InvestmentMemo.id == memo_id))
    assert memo is not None
    assert memo.status == MemoStatus.PENDING
    assert memo.title == "TSLA 2025 Analysis"

    task_res = generate_memo_task.run(str(memo_id))
    assert task_res["status"] == "COMPLETED"

    # 4. Verify DB state after task run
    sync_session.expire_all()
    memo = sync_session.scalar(select(InvestmentMemo).where(InvestmentMemo.id == memo_id))
    assert memo.status == MemoStatus.COMPLETED
    assert memo.executive_summary is not None
    assert len(memo.sections) == 8  # Fallback generates exactly 8 sections

    # 5. Fetch details via API GET
    get_resp = await api_client.get(f"{PREFIX}/memos/{memo_id}")
    assert get_resp.status_code == 200, get_resp.text
    get_data = get_resp.json()
    assert get_data["status"] == "COMPLETED"
    assert len(get_data["sections"]) == 8
    assert get_data["sections"][0]["section_name"] == "Company Overview"

    # 6. Fetch citations via API GET
    cit_resp = await api_client.get(f"{PREFIX}/memos/{memo_id}/citations")
    assert cit_resp.status_code == 200, cit_resp.text
    cit_data = cit_resp.json()
    assert len(cit_data) > 0
    assert cit_data[0]["source_type"] == "text_chunk"

    # 7. Export via API GET (Markdown)
    export_md_resp = await api_client.get(f"{PREFIX}/memos/{memo_id}/export?format=markdown")
    assert export_md_resp.status_code == 200, export_md_resp.text
    export_md_data = export_md_resp.json()
    assert export_md_data["format"] == "markdown"
    assert "Investment Memo: Tesla Inc (FY 2025)" in export_md_data["exported_content"]
    assert "Company Overview" in export_md_data["exported_content"]

    # Export via API GET (JSON)
    export_json_resp = await api_client.get(f"{PREFIX}/memos/{memo_id}/export?format=json")
    assert export_json_resp.status_code == 200, export_json_resp.text
    export_json_data = export_json_resp.json()
    assert export_json_data["format"] == "json"
    exported_obj = json.loads(export_json_data["exported_content"])
    assert exported_obj["status"] == "COMPLETED"
    assert len(exported_obj["sections"]) == 8
