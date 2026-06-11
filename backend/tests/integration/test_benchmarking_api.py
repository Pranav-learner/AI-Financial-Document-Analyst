"""Integration tests for Competitor Benchmarking Engine APIs and Celery Tasks (Phase 8)."""

from __future__ import annotations

import uuid
from decimal import Decimal
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.company import Company
from app.models.enums import ReportStatus
from app.models.financial_metric import FinancialMetric
from app.models.management_tone import ManagementTone
from app.models.risk_factor import RiskFactor
from app.models.report import Report
from app.models.benchmark import BenchmarkRun, BenchmarkResult, BenchmarkSummary, BenchmarkStatus
from app.tasks.benchmark import run_benchmark_task

PREFIX = settings.api_v1_prefix


def _seed_cohort_data(session: Session) -> list[uuid.UUID]:
    # Create 3 companies
    c1 = Company(name="Apple Inc", ticker="AAPL")
    c2 = Company(name="Microsoft Corp", ticker="MSFT")
    c3 = Company(name="Google LLC", ticker="GOOG")
    session.add_all([c1, c2, c3])
    session.commit()

    companies = [c1, c2, c3]
    for idx, c in enumerate(companies):
        r = Report(
            company_id=c.id,
            report_type="10-K",
            year=2024,
            original_filename="x.pdf",
            storage_path=f"reports/2026/06/{c.ticker}_2024.pdf",
            status=ReportStatus.COMPARED,
            total_pages=1,
        )
        session.add(r)
        session.commit()

        # Seed Financial Metric: Revenue growth
        #AAPL: 10.0%, MSFT: 15.0%, GOOG: 8.0%
        rev_growth = 10.0 if idx == 0 else (15.0 if idx == 1 else 8.0)
        session.add(
            FinancialMetric(
                report_id=r.id,
                metric_name="REVENUE_GROWTH",
                normalized_metric_name="REVENUE_GROWTH",
                metric_category="PROFITABILITY",
                value=Decimal(str(rev_growth)),
                currency="PERCENT",
                unit="PERCENTAGE",
                fiscal_year=2024,
                fiscal_quarter=None,
                confidence_score=Decimal("1.0"),
                extraction_method="RULE_BASED",
                source_text="seed",
            )
        )

        # Seed Risk Factor: Cyber/regulatory severity
        #AAPL: HIGH, MSFT: MEDIUM, GOOG: LOW
        risk_sev = "HIGH" if idx == 0 else ("MEDIUM" if idx == 1 else "LOW")
        session.add(
            RiskFactor(
                company_id=c.id,
                report_id=r.id,
                risk_name="regulatory risk",
                normalized_risk_name="regulatory_risk",
                risk_description="desc",
                category="REGULATORY",
                severity=risk_sev,
                confidence_score=Decimal("0.9"),
                extraction_method="RULE_BASED",
                source_text="seed",
            )
        )

        # Seed Management Tone: Positive / Hedging
        #AAPL: 10.0% hedging, MSFT: 5.0% hedging, GOOG: 12.0% hedging
        hedge_score = 0.10 if idx == 0 else (0.05 if idx == 1 else 0.12)
        session.add(
            ManagementTone(
                company_id=c.id,
                report_id=r.id,
                source_type="MDA",
                sentiment="POSITIVE",
                confidence_level="CONFIDENT",
                hedging_score=Decimal(str(hedge_score)),
                positive_score=Decimal("0.8"),
                negative_score=Decimal("0.1"),
                confidence_score=Decimal("0.9"),
                extraction_method="RULE_BASED",
                source_text="seed",
            )
        )

        # Seed Capital Allocation: R&D Expense / Capex
        #AAPL: 200.0, MSFT: 300.0, GOOG: 150.0
        capex = 200.0 if idx == 0 else (300.0 if idx == 1 else 150.0)
        session.add(
            FinancialMetric(
                report_id=r.id,
                metric_name="CAPEX",
                normalized_metric_name="CAPEX",
                metric_category="CASH_FLOW",
                value=Decimal(str(capex)),
                currency="USD",
                unit="ABSOLUTE",
                fiscal_year=2024,
                fiscal_quarter=None,
                confidence_score=Decimal("1.0"),
                extraction_method="RULE_BASED",
                source_text="seed",
            )
        )
        session.commit()

    return [c.id for c in companies]


@pytest.mark.integration
async def test_sync_cohort_comparison_api(api_client: AsyncClient, sync_session: Session) -> None:
    """Test the synchronous comparison API."""
    company_ids = _seed_cohort_data(sync_session)

    payload = {
        "company_ids": [str(cid) for cid in company_ids],
        "configuration": {
            "weights": {
                "financial": 0.40,
                "risk": 0.20,
                "tone": 0.20,
                "capital_allocation": 0.20,
            },
            "tie_method": "min",
        },
    }

    response = await api_client.post(f"{PREFIX}/benchmark/compare", json=payload)
    assert response.status_code == 200
    data = response.json()

    # Verify response schema
    assert "cohort_results" in data
    assert "cohort_summaries" in data
    assert len(data["cohort_summaries"]) == 3
    assert len(data["cohort_results"]) == 25  # 25 metrics total in METRIC_DIRECTIONS

    # Verify ranking correctness: MSFT (idx 1) should be #1
    summaries = sorted(data["cohort_summaries"], key=lambda x: x["rank"])
    assert summaries[0]["company_id"] == str(company_ids[1])
    assert summaries[0]["rank"] == 1


@pytest.mark.integration
async def test_async_benchmark_lifecycle_api(api_client: AsyncClient, sync_session: Session) -> None:
    """Test create run -> check status -> run celery task -> check results/summary APIs."""
    company_ids = _seed_cohort_data(sync_session)

    run_payload = {
        "run_name": "Q4 Cohort Benchmarking",
        "company_ids": [str(cid) for cid in company_ids],
        "benchmark_type": "COHORT_ANALYSIS",
        "configuration": {
            "weights": {
                "financial": 0.35,
                "risk": 0.25,
                "tone": 0.20,
                "capital_allocation": 0.20,
            },
            "tie_method": "dense",
        },
    }

    # 1. Create run
    resp = await api_client.post(f"{PREFIX}/benchmark/run", json=run_payload)
    assert resp.status_code == 202
    run_data = resp.json()
    assert run_data["status"] == "PENDING"
    run_id = run_data["id"]

    # 2. Get status of run (should be PENDING)
    resp = await api_client.get(f"{PREFIX}/benchmark/{run_id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "PENDING"

    # 3. Invoke the core benchmark processing directly
    from app.db.session import AsyncSessionLocal
    from app.benchmarking.benchmark_service import BenchmarkService
    async with AsyncSessionLocal() as session:
        service = BenchmarkService(session)
        await service.run_benchmark(uuid.UUID(run_id))

    # 4. Get status of run again (should be COMPLETED)
    resp = await api_client.get(f"{PREFIX}/benchmark/{run_id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "COMPLETED"

    # 5. Fetch detailed dimension results
    resp = await api_client.get(f"{PREFIX}/benchmark/{run_id}/results")
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 75

    # 6. Fetch company-level ranking summaries
    resp = await api_client.get(f"{PREFIX}/benchmark/{run_id}/summary")
    assert resp.status_code == 200
    summaries = resp.json()
    assert len(summaries) == 3

    # Check that MSFT is ranked 1
    summaries_sorted = sorted(summaries, key=lambda x: x["rank"])
    assert summaries_sorted[0]["company_id"] == str(company_ids[1])
    assert summaries_sorted[0]["rank"] == 1


@pytest.mark.integration
async def test_benchmark_404_errors(api_client: AsyncClient) -> None:
    """Test 404 responses for non-existent benchmark run IDs."""
    fake_id = str(uuid.uuid4())
    resp = await api_client.get(f"{PREFIX}/benchmark/{fake_id}")
    assert resp.status_code == 404

    resp = await api_client.get(f"{PREFIX}/benchmark/{fake_id}/results")
    assert resp.status_code == 404

    resp = await api_client.get(f"{PREFIX}/benchmark/{fake_id}/summary")
    assert resp.status_code == 404
