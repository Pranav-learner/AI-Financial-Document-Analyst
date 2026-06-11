"""Comparison builder for extracting cohort company metrics across dimensions (Phase 8)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.benchmark import BenchmarkRun
from app.models.company import Company
from app.models.financial_metric import FinancialMetric
from app.models.management_tone import ManagementTone
from app.models.metric_comparison import MetricComparison
from app.models.report import Report
from app.models.risk_evolution import RiskEvolution
from app.models.risk_factor import RiskFactor


class ComparisonBuilder:
    """Extracts raw benchmarking metrics for companies from their latest reports."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_latest_report(
        self, company_id: uuid.UUID, year_override: int | None = None
    ) -> Report | None:
        """Fetch the latest report for a company, optionally filtered by year."""
        stmt = select(Report).where(Report.company_id == company_id)
        if year_override is not None:
            stmt = stmt.where(Report.year == year_override)
        # Sort by year desc, then quarter desc, then uploaded_at desc to find latest
        stmt = stmt.order_by(Report.year.desc(), Report.quarter.desc(), Report.uploaded_at.desc())
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_previous_report(self, company_id: uuid.UUID, current_report: Report) -> Report | None:
        """Fetch the report immediately preceding the current report."""
        stmt = select(Report).where(
            Report.company_id == company_id,
            Report.id != current_report.id
        )
        # We look for a report in the same or previous years
        stmt = stmt.where(
            (Report.year < current_report.year) |
            ((Report.year == current_report.year) & (Report.quarter < current_report.quarter))
        ) if current_report.quarter is not None else stmt.where(Report.year < current_report.year)

        stmt = stmt.order_by(Report.year.desc(), Report.quarter.desc(), Report.uploaded_at.desc())
        result = await self.db.execute(stmt)
        return result.scalars().first()

    @staticmethod
    def _find_metric(metrics: list[FinancialMetric], aliases: list[str]) -> FinancialMetric | None:
        for m in metrics:
            if m.normalized_metric_name in aliases:
                return m
            if m.metric_name.upper() in aliases:
                return m
        return None

    def _find_yoy_growth(
        self,
        comparisons: list[MetricComparison],
        metrics: list[FinancialMetric],
        aliases: list[str],
        prev_metrics: list[FinancialMetric] | None = None,
    ) -> float | None:
        # 1. Check direct metric comparisons (YoY)
        for c in comparisons:
            if c.metric_name in aliases and c.comparison_type == "YOY":
                if c.percentage_change is not None:
                    return float(c.percentage_change)

        # 2. Check if a growth metric was extracted directly
        growth_aliases = [f"{a}_GROWTH" for a in aliases]
        m_growth = self._find_metric(metrics, growth_aliases)
        if m_growth is not None and m_growth.value is not None:
            return float(m_growth.value)

        # 3. Calculate from current vs previous metrics
        curr = self._find_metric(metrics, aliases)
        if curr is not None and curr.value is not None and prev_metrics is not None:
            prev = self._find_metric(prev_metrics, aliases)
            if prev is not None and prev.value is not None and float(prev.value) != 0.0:
                return ((float(curr.value) - float(prev.value)) / float(prev.value)) * 100.0

        return None

    @staticmethod
    def _calculate_std_dev(values: list[float]) -> float:
        n = len(values)
        if n <= 1:
            return 0.0
        mean = sum(values) / n
        variance = sum((x - mean) ** 2 for x in values) / n
        return variance ** 0.5

    async def extract_company_data(
        self, company_id: uuid.UUID, year_override: int | None = None
    ) -> dict[str, Any] | None:
        """Extract all benchmarking metrics for a company's latest report."""
        report = await self.get_latest_report(company_id, year_override)
        if not report:
            return None

        # Fetch previous report for growth calculations
        prev_report = await self.get_previous_report(company_id, report)

        # Load current metrics
        metrics_stmt = select(FinancialMetric).where(FinancialMetric.report_id == report.id)
        metrics_res = await self.db.execute(metrics_stmt)
        metrics = list(metrics_res.scalars().all())

        # Load previous metrics if possible
        prev_metrics: list[FinancialMetric] | None = None
        if prev_report:
            prev_metrics_stmt = select(FinancialMetric).where(FinancialMetric.report_id == prev_report.id)
            prev_metrics_res = await self.db.execute(prev_metrics_stmt)
            prev_metrics = list(prev_metrics_res.scalars().all())

        # Load current comparisons
        comp_stmt = select(MetricComparison).where(MetricComparison.company_id == company_id)
        comp_res = await self.db.execute(comp_stmt)
        comparisons = list(comp_res.scalars().all())

        # Load current risks
        risks_stmt = select(RiskFactor).where(RiskFactor.report_id == report.id)
        risks_res = await self.db.execute(risks_stmt)
        risks = list(risks_res.scalars().all())

        # Load current risk evolutions
        risk_ev_stmt = (
            select(RiskEvolution)
            .join(RiskFactor, RiskEvolution.current_risk_id == RiskFactor.id)
            .where(RiskFactor.report_id == report.id)
        )
        risk_ev_res = await self.db.execute(risk_ev_stmt)
        risk_evs = list(risk_ev_res.scalars().all())

        # Load current tone
        tone_stmt = select(ManagementTone).where(ManagementTone.report_id == report.id)
        tone_res = await self.db.execute(tone_stmt)
        tones = list(tone_res.scalars().all())

        # Load previous tone for evolution calculation
        prev_tones: list[ManagementTone] = []
        if prev_report:
            prev_tone_stmt = select(ManagementTone).where(ManagementTone.report_id == prev_report.id)
            prev_tone_res = await self.db.execute(prev_tone_stmt)
            prev_tones = list(prev_tone_res.scalars().all())

        # --- FINANCIAL DIMENSION ---
        revenue_aliases = ["REVENUE", "TOTAL_REVENUE", "SALES", "NET_SALES"]
        ebitda_aliases = ["EBITDA", "OPERATING_EBITDA"]
        net_inc_aliases = ["NET_INCOME", "NET_PROFIT", "NET_EARNINGS"]
        fcf_aliases = ["FREE_CASH_FLOW", "FCF"]
        debt_aliases = ["TOTAL_DEBT", "DEBT"]
        ocf_aliases = ["OPERATING_CASH_FLOW", "CASH_FROM_OPERATIONS", "CASH_FLOW_OPERATIONS"]

        rev_growth = self._find_yoy_growth(comparisons, metrics, revenue_aliases, prev_metrics)
        ebitda_growth = self._find_yoy_growth(comparisons, metrics, ebitda_aliases, prev_metrics)
        net_inc_growth = self._find_yoy_growth(comparisons, metrics, net_inc_aliases, prev_metrics)
        fcf_growth = self._find_yoy_growth(comparisons, metrics, fcf_aliases, prev_metrics)

        # Margins & Leverage
        op_margin_m = self._find_metric(metrics, ["OPERATING_MARGIN"])
        op_margin = float(op_margin_m.value) if op_margin_m and op_margin_m.value is not None else None
        if op_margin is None:
            op_inc = self._find_metric(metrics, ["OPERATING_INCOME", "OPERATING_PROFIT", "EBIT"])
            rev = self._find_metric(metrics, revenue_aliases)
            if op_inc and op_inc.value is not None and rev and rev.value:
                op_margin = (float(op_inc.value) / float(rev.value)) * 100.0

        net_margin_m = self._find_metric(metrics, ["NET_MARGIN"])
        net_margin = float(net_margin_m.value) if net_margin_m and net_margin_m.value is not None else None
        if net_margin is None:
            net_inc = self._find_metric(metrics, net_inc_aliases)
            rev = self._find_metric(metrics, revenue_aliases)
            if net_inc and net_inc.value is not None and rev and rev.value:
                net_margin = (float(net_inc.value) / float(rev.value)) * 100.0

        debt_to_rev_m = self._find_metric(metrics, ["DEBT_TO_REVENUE"])
        debt_to_rev = float(debt_to_rev_m.value) if debt_to_rev_m and debt_to_rev_m.value is not None else None
        if debt_to_rev is None:
            debt = self._find_metric(metrics, debt_aliases)
            rev = self._find_metric(metrics, revenue_aliases)
            if debt and debt.value is not None and rev and rev.value:
                debt_to_rev = (float(debt.value) / float(rev.value)) * 100.0

        cf_margin_m = self._find_metric(metrics, ["CASH_FLOW_MARGIN"])
        cf_margin = float(cf_margin_m.value) if cf_margin_m and cf_margin_m.value is not None else None
        if cf_margin is None:
            ocf = self._find_metric(metrics, ocf_aliases)
            rev = self._find_metric(metrics, revenue_aliases)
            if ocf and ocf.value is not None and rev and rev.value:
                cf_margin = (float(ocf.value) / float(rev.value)) * 100.0

        # --- RISK DIMENSION ---
        total_risks = len(risks)
        high_severity_risks = sum(1 for r in risks if r.severity == "HIGH")
        critical_risks = sum(1 for r in risks if r.severity == "CRITICAL")
        new_risks = sum(1 for r in risk_evs if r.evolution_type == "NEW_RISK")
        escalated_risks = sum(1 for r in risk_evs if r.evolution_type == "ESCALATED_RISK")

        pages = report.total_pages or 1
        risk_density = total_risks / pages if pages > 0 else 0.0

        # --- TONE DIMENSION ---
        sentiment_scores = [float(t.positive_score - t.negative_score) for t in tones if t.positive_score is not None and t.negative_score is not None]
        sentiment_score = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else None

        confidence_scores = [float(t.confidence_score) for t in tones if t.confidence_score is not None]
        confidence_score = sum(confidence_scores) / len(confidence_scores) if confidence_scores else None

        hedging_scores = [float(t.hedging_score) for t in tones if t.hedging_score is not None]
        hedging_score = sum(hedging_scores) / len(hedging_scores) if hedging_scores else None

        tone_stability = None
        if sentiment_scores:
            std_dev = self._calculate_std_dev(sentiment_scores)
            tone_stability = max(0.0, 1.0 - std_dev)

        conf_evolution = None
        if confidence_score is not None and prev_tones:
            prev_conf_scores = [float(t.confidence_score) for t in prev_tones if t.confidence_score is not None]
            if prev_conf_scores:
                prev_conf_avg = sum(prev_conf_scores) / len(prev_conf_scores)
                conf_evolution = confidence_score - prev_conf_avg

        # --- CAPITAL ALLOCATION DIMENSION ---
        capex_aliases = ["CAPEX", "CAPITAL_EXPENDITURES", "CAPITAL_EXPENDITURE", "CAPITAL_SPENDING"]
        capex_m = self._find_metric(metrics, capex_aliases)
        capex = float(capex_m.value) if capex_m and capex_m.value is not None else None
        capex_growth = self._find_yoy_growth(comparisons, metrics, capex_aliases, prev_metrics)

        # Debt Reduction (inverted growth)
        debt_growth = self._find_yoy_growth(comparisons, metrics, debt_aliases, prev_metrics)
        debt_reduction = -debt_growth if debt_growth is not None else None

        # Cash deployment (CAPEX + Buybacks + Dividends)
        div_aliases = ["DIVIDENDS", "DIVIDEND_PAYMENTS", "DIVIDEND_YIELD"]
        div_m = self._find_metric(metrics, div_aliases)
        div_val = float(div_m.value) if div_m and div_m.value is not None else 0.0

        buyback_aliases = ["BUYBACKS", "SHARE_REPURCHASES", "STOCK_REPURCHASES"]
        buyback_m = self._find_metric(metrics, buyback_aliases)
        buyback_val = float(buyback_m.value) if buyback_m and buyback_m.value is not None else 0.0

        cash_deployment = None
        if capex is not None:
            cash_deployment = capex + abs(div_val) + abs(buyback_val)

        dividend_metric = float(div_m.value) if div_m and div_m.value is not None else None
        buyback_metric = float(buyback_m.value) if buyback_m and buyback_m.value is not None else None

        return {
            "report_id": report.id,
            "financial": {
                "REVENUE_GROWTH": rev_growth,
                "EBITDA_GROWTH": ebitda_growth,
                "NET_INCOME_GROWTH": net_inc_growth,
                "FCF_GROWTH": fcf_growth,
                "OPERATING_MARGIN": op_margin,
                "NET_MARGIN": net_margin,
                "DEBT_TO_REVENUE": debt_to_rev,
                "CASH_FLOW_MARGIN": cf_margin,
            },
            "risk": {
                "TOTAL_RISKS": total_risks,
                "HIGH_SEVERITY_RISKS": high_severity_risks,
                "CRITICAL_RISKS": critical_risks,
                "NEW_RISKS": new_risks,
                "ESCALATED_RISKS": escalated_risks,
                "RISK_DENSITY": risk_density,
            },
            "tone": {
                "SENTIMENT_SCORE": sentiment_score,
                "CONFIDENCE_SCORE": confidence_score,
                "HEDGING_SCORE": hedging_score,
                "TONE_STABILITY": tone_stability,
                "CONFIDENCE_EVOLUTION": conf_evolution,
            },
            "capital_allocation": {
                "CAPEX": capex,
                "CAPEX_GROWTH": capex_growth,
                "DEBT_REDUCTION": debt_reduction,
                "CASH_DEPLOYMENT": cash_deployment,
                "DIVIDEND_METRICS": dividend_metric,
                "BUYBACK_METRICS": buyback_metric,
            },
        }
