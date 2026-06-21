"""Unit tests for Phase 9 Investment Memo Generation Engine."""

from __future__ import annotations

import uuid
import pytest
from unittest.mock import MagicMock, patch

from app.models.enums import MemoStatus, MemoType
from app.memo.exceptions import MemoValidationError
from app.memo.memo_models import (
    MemoPackage,
    FinancialMetricPack,
    MetricComparisonPack,
    FinancialAnalyticsPack,
    RiskFactorPack,
    ManagementTonePack,
    BenchmarkSummaryPack,
    TextChunkPack,
    CitationSchema,
    MemoSectionSchema,
)
from app.memo.citation_builder import CitationBuilder
from app.memo.memo_validator import MemoValidator
from app.memo.memo_builder import MemoBuilder


@pytest.fixture
def sample_package() -> MemoPackage:
    report_id = uuid.uuid4()
    chunk_1_id = uuid.uuid4()
    chunk_2_id = uuid.uuid4()
    risk_id = uuid.uuid4()

    return MemoPackage(
        company_name="Acme Corp",
        report_id=report_id,
        report_title="FY2025 Annual Report",
        reporting_year=2025,
        reporting_period="FY",
        financial_metrics=[
            FinancialMetricPack(name="Revenue", value=150000000.0, unit="USD", period="FY2025", category="REVENUE"),
            FinancialMetricPack(name="Net Income", value=15000000.0, unit="USD", period="FY2025", category="PROFITABILITY"),
        ],
        comparisons=[
            MetricComparisonPack(metric_name="Revenue", comparison_type="YOY", current_value=150000000.0, previous_value=120000000.0, change_pct=25.0),
        ],
        analytics=[
            FinancialAnalyticsPack(signal_type="GROWTH", metric_name="Revenue", trend="UPWARD", strength=80.0, score=85.0, explanation="Strong top-line growth"),
        ],
        risks=[
            RiskFactorPack(id=risk_id, category="OPERATIONAL", severity="HIGH", description="Supply chain delays in key logistics centers.", source_chunk_id=chunk_2_id, page_number=14),
        ],
        tones=[
            ManagementTonePack(sentiment="POSITIVE", confidence_level="CONFIDENT", hedging_score=0.25, sentiment_score=0.75, source_chunk_id=chunk_1_id),
        ],
        benchmark=BenchmarkSummaryPack(overall_score=78.5, financial_score=82.0, risk_score=75.0, tone_score=70.0, capital_allocation_score=88.0, rank=2),
        retrieved_evidence=[
            TextChunkPack(id=chunk_1_id, content="Management feels confident about the expansion plans in Europe.", page_number=2, section_name="Overview"),
            TextChunkPack(id=chunk_2_id, content="Operational risks include supply chain delays and logistical constraints.", page_number=14, section_name="Risk Factors"),
        ],
    )


@pytest.mark.unit
def test_citation_builder_exact_lookup(sample_package: MemoPackage) -> None:
    builder = CitationBuilder(sample_package)
    chunk_1_id = sample_package.retrieved_evidence[0].id
    
    raw_citations = [
        {"source_type": "text_chunk", "chunk_id": str(chunk_1_id), "text_snippet": "expansion plans"},
        {"source_type": "risk_factor", "chunk_id": str(sample_package.risks[0].id)},
    ]

    resolved = builder.resolve_and_validate(raw_citations)
    assert len(resolved) == 2
    assert resolved[0].chunk_id == chunk_1_id
    assert resolved[0].page_number == 2
    assert resolved[0].source_type == "text_chunk"
    
    assert resolved[1].chunk_id == sample_package.risks[0].source_chunk_id
    assert resolved[1].page_number == 14
    assert resolved[1].source_type == "risk_factor"


@pytest.mark.unit
def test_citation_builder_jaccard_fallback(sample_package: MemoPackage) -> None:
    builder = CitationBuilder(sample_package)
    
    # Text snippet containing keywords from the second chunk
    raw_citations = [
        {"source_type": "text_chunk", "text_snippet": "supply chain delays and operational constraints"},
    ]

    resolved = builder.resolve_and_validate(raw_citations)
    assert len(resolved) == 1
    assert resolved[0].chunk_id == sample_package.retrieved_evidence[1].id
    assert resolved[0].page_number == 14
    assert resolved[0].source_type == "text_chunk"


@pytest.mark.unit
def test_memo_validator_prohibited_ratings(sample_package: MemoPackage) -> None:
    validator = MemoValidator()
    
    # Violates rating check
    sections = [
        MemoSectionSchema(
            section_name="Overview",
            section_order=1,
            content="This company represents a strong buy recommendation.",
            citations=[]
        )
    ]
    
    with pytest.raises(MemoValidationError, match="violates negative constraints"):
        validator.validate(sample_package, "Summary", sections)

    # Violates target price check
    sections_target = [
        MemoSectionSchema(
            section_name="Overview",
            section_order=1,
            content="Our price target is $150.",
            citations=[]
        )
    ]
    with pytest.raises(MemoValidationError, match="violates negative constraints"):
        validator.validate(sample_package, "Summary", sections_target)


@pytest.mark.unit
def test_memo_validator_grounding_verification(sample_package: MemoPackage) -> None:
    validator = MemoValidator()
    
    # Contains a grounded number (150,000,000 and 25%)
    sections_valid = [
        MemoSectionSchema(
            section_name="Overview",
            section_order=1,
            content="Acme Corp reported revenue of 150,000,000 representing 25% growth.",
            citations=[]
        )
    ]
    # Should not raise exception
    validator.validate(sample_package, "Summary", sections_valid)

    # Contains multiple ungrounded numbers (999,999, 888,888, 777,777, 666,666, 555,555)
    sections_invalid = [
        MemoSectionSchema(
            section_name="Overview",
            section_order=1,
            content="The company has 999,999 active users in Europe, 888,888 in Asia, 777,777 in America, 666,666 in Africa, and 555,555 in Australia.",
            citations=[]
        )
    ]
    with pytest.raises(MemoValidationError, match="contains 5 ungrounded figures"):
        validator.validate(sample_package, "Summary", sections_invalid)



@pytest.mark.unit
def test_memo_builder_fallback_trigger(sample_package: MemoPackage) -> None:
    # Build with no api_key to force fallback
    builder = MemoBuilder(api_key=None)
    res = builder.generate(sample_package)
    
    assert "Acme Corp" in res["title"]
    assert len(res["sections"]) == 8
    assert res["sections"][0].section_name == "Company Overview"
    assert "FY2025" in res["sections"][0].content
    assert res["sections"][1].section_name == "Financial Summary"
    assert "Revenue" in res["sections"][1].content
