"""Package builder for Phase 9: Investment Memo Generation Engine."""

from __future__ import annotations

import uuid
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.company import Company
from app.models.report import Report
from app.models.financial_metric import FinancialMetric
from app.models.metric_comparison import MetricComparison
from app.models.financial_analytics import FinancialAnalytics
from app.models.risk_factor import RiskFactor
from app.models.management_tone import ManagementTone
from app.models.benchmark import BenchmarkSummary
from app.models.document_chunk import DocumentChunk
from app.memo.exceptions import InvalidMemoPackageError
from app.memo.memo_models import (
    MemoPackage,
    FinancialMetricPack,
    MetricComparisonPack,
    FinancialAnalyticsPack,
    RiskFactorPack,
    ManagementTonePack,
    BenchmarkSummaryPack,
    TextChunkPack,
)


class MemoPackageBuilder:
    """Retrieves, structures, and packages all computed intelligence and evidence chunks."""

    def __init__(self, db: Session):
        self.db = db

    def build(self, company_id: uuid.UUID, report_id: uuid.UUID, benchmark_run_id: uuid.UUID | None = None) -> MemoPackage:
        """Queries and aggregates all relevant intelligence data into a unified MemoPackage."""
        
        # 1. Fetch Company
        company = self.db.scalar(select(Company).where(Company.id == company_id))
        if not company:
            raise InvalidMemoPackageError(f"Company not found: {company_id}")

        # 2. Fetch Report
        report = self.db.scalar(select(Report).where(Report.id == report_id))
        if not report:
            raise InvalidMemoPackageError(f"Report not found: {report_id}")

        # 3. Fetch Financial Metrics
        metrics = self.db.scalars(
            select(FinancialMetric).where(FinancialMetric.report_id == report_id)
        ).all()
        metric_packs = [
            FinancialMetricPack(
                name=m.metric_name,
                value=float(m.value) if m.value is not None else None,
                unit=m.unit,
                period=f"FY{m.fiscal_year}" if m.fiscal_year else None,
                category=m.metric_category,
            )
            for m in metrics
        ]

        # 4. Fetch Metric Comparisons
        comparisons = self.db.scalars(
            select(MetricComparison).where(MetricComparison.company_id == company_id)
        ).all()
        comp_packs = [
            MetricComparisonPack(
                metric_name=c.metric_name,
                comparison_type=c.comparison_type,
                current_value=float(c.current_value) if c.current_value is not None else None,
                previous_value=float(c.previous_value) if c.previous_value is not None else None,
                change_pct=float(c.percentage_change) if c.percentage_change is not None else None,
            )
            for c in comparisons
        ]

        # 5. Fetch Financial Analytics
        analytics = self.db.scalars(
            select(FinancialAnalytics).where(FinancialAnalytics.report_id == report_id)
        ).all()
        anal_packs = [
            FinancialAnalyticsPack(
                signal_type=a.signal_type,
                metric_name=a.metric_name or "Overall",
                trend=a.signal_code,
                strength=float(a.value) if a.value is not None else None,
                score=float(a.value) if a.value is not None else None,
                explanation=a.explanation,
            )
            for a in analytics
        ]

        # 6. Fetch Risk Factors
        risks = self.db.scalars(
            select(RiskFactor).where(RiskFactor.report_id == report_id)
        ).all()
        
        chunk_page_map = {}
        chunk_ids = [r.source_chunk_id for r in risks if r.source_chunk_id]
        if chunk_ids:
            chunks = self.db.scalars(
                select(DocumentChunk).where(DocumentChunk.id.in_(chunk_ids))
            ).all()
            chunk_page_map = {c.id: c.start_page for c in chunks}

        risk_packs = [
            RiskFactorPack(
                id=r.id,
                category=r.category.value if hasattr(r.category, 'value') else str(r.category),
                severity=r.severity.value if hasattr(r.severity, 'value') else str(r.severity),
                description=r.risk_description,
                source_chunk_id=r.source_chunk_id,
                page_number=chunk_page_map.get(r.source_chunk_id) if r.source_chunk_id else None,
            )
            for r in risks
        ]

        # 7. Fetch Management Tones
        tones = self.db.scalars(
            select(ManagementTone).where(ManagementTone.report_id == report_id)
        ).all()
        tone_packs = [
            ManagementTonePack(
                sentiment=t.sentiment.value if hasattr(t.sentiment, 'value') else str(t.sentiment),
                confidence_level=t.confidence_level.value if hasattr(t.confidence_level, 'value') else str(t.confidence_level),
                hedging_score=float(t.hedging_score),
                sentiment_score=float(t.positive_score - t.negative_score),
                source_chunk_id=t.source_chunk_id,
            )
            for t in tones
        ]

        # 8. Fetch Benchmark Summary if requested
        bench_pack = None
        if benchmark_run_id:
            bench = self.db.scalar(
                select(BenchmarkSummary).where(
                    BenchmarkSummary.benchmark_run_id == benchmark_run_id,
                    BenchmarkSummary.company_id == company_id,
                )
            )
            if bench:
                bench_pack = BenchmarkSummaryPack(
                    overall_score=float(bench.overall_score) if bench.overall_score is not None else None,
                    financial_score=float(bench.financial_score) if bench.financial_score is not None else None,
                    risk_score=float(bench.risk_score) if bench.risk_score is not None else None,
                    tone_score=float(bench.tone_score) if bench.tone_score is not None else None,
                    capital_allocation_score=float(bench.capital_allocation_score) if bench.capital_allocation_score is not None else None,
                    rank=bench.rank,
                )

        # 9. Fetch top relevant text chunks
        chunks = self.db.scalars(
            select(DocumentChunk)
            .where(DocumentChunk.report_id == report_id)
            .order_by(DocumentChunk.start_page, DocumentChunk.chunk_index)
            .limit(20)
        ).all()
        chunk_packs = [
            TextChunkPack(
                id=c.id,
                content=c.chunk_text,
                page_number=c.start_page or 1,
                section_name=c.chunk_metadata.get("section_name") if c.chunk_metadata else None,
            )
            for c in chunks
        ]

        rep_type_val = report.report_type.value if hasattr(report.report_type, "value") else str(report.report_type)
        report_title = f"{company.name} {rep_type_val} FY{report.year}"
        reporting_year = report.year
        reporting_period = "FY" if rep_type_val == "10-K" else "Q"

        return MemoPackage(
            company_name=company.name,
            report_id=report.id,
            report_title=report_title,
            reporting_year=reporting_year,
            reporting_period=reporting_period,
            financial_metrics=metric_packs,
            comparisons=comp_packs,
            analytics=anal_packs,
            risks=risk_packs,
            tones=tone_packs,
            benchmark=bench_pack,
            retrieved_evidence=chunk_packs,
        )
