"""Signal Generator — generates financial signals deterministically (Phase 3C)."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import List, Dict, Optional

from app.models.financial_metric import FinancialMetric
from app.models.metric_comparison import MetricComparison
from app.financial.analytics.analytics_models import CalculatedRatio, GeneratedSignal
from app.financial.analytics.trend_classifier import TrendClassifier


class SignalGenerator:
    """Generates deterministic financial signals from metrics, comparisons, and ratios."""

    def __init__(self, classifier: TrendClassifier | None = None) -> None:
        self.classifier = classifier or TrendClassifier()

    def generate_signals(
        self,
        metrics: list[FinancialMetric],
        comparisons: list[MetricComparison],
        ratios: list[CalculatedRatio],
        company_historical_metrics: list[FinancialMetric] = None,
    ) -> list[GeneratedSignal]:
        signals: list[GeneratedSignal] = []

        # Lookups
        metric_by_name: dict[str, FinancialMetric] = {m.normalized_metric_name: m for m in metrics}
        comp_by_key: dict[tuple[str, str], MetricComparison] = {
            (c.metric_name, c.comparison_type): c for c in comparisons
        }

        # Helper to format percentage
        def fmt_pct(val: Decimal | None) -> str:
            if val is None:
                return "N/A"
            return f"{val * Decimal('100'):+.2f}%"

        # Helper to format currency/value
        def fmt_val(val: Decimal | None) -> str:
            if val is None:
                return "N/A"
            # simple format
            return f"{val:,.2f}"

        # 1. Growth & Profitability Signals from Comparisons
        for (m_name, comp_type), comp in comp_by_key.items():
            # Standard Growth Metrics
            if m_name in ("REVENUE", "NET_INCOME", "EBITDA", "OPERATING_CASH_FLOW", "FREE_CASH_FLOW"):
                if comp.percentage_change is not None:
                    pct = Decimal(str(comp.percentage_change))
                    trend = self.classifier.classify_growth(pct)
                    
                    # Determine type and code
                    sig_type = "GROWTH"
                    if m_name in ("NET_INCOME", "EBITDA"):
                        sig_type = "PROFITABILITY"
                    elif m_name in ("OPERATING_CASH_FLOW", "FREE_CASH_FLOW"):
                        sig_type = "CASH_FLOW"

                    # Severity mapping
                    severity = "NEUTRAL"
                    if trend == "STRONG_GROWTH":
                        severity = "VERY_POSITIVE"
                    elif trend == "MODERATE_GROWTH":
                        severity = "POSITIVE"
                    elif trend == "LOW_GROWTH":
                        severity = "NEUTRAL"
                    elif trend == "DECLINING":
                        severity = "NEGATIVE"

                    code = f"{m_name}_GROWTH_{comp_type}"
                    expl = f"{m_name.replace('_', ' ').title()} grew by {fmt_pct(pct)} {comp_type} (from {fmt_val(Decimal(str(comp.previous_value)))} to {fmt_val(Decimal(str(comp.current_value)))})."

                    signals.append(
                        GeneratedSignal(
                            signal_type=sig_type,
                            signal_code=code,
                            metric_name=m_name,
                            value=pct,
                            classification=trend,
                            severity=severity,
                            supporting_metric_ids=[comp.metric_id],
                            explanation=expl,
                        )
                    )

            # Margin Changes (absolute changes)
            elif m_name in ("GROSS_MARGIN", "OPERATING_MARGIN", "NET_MARGIN"):
                if comp.absolute_change is not None:
                    diff = Decimal(str(comp.absolute_change))
                    trend = self.classifier.classify_margin_change(diff)
                    
                    severity = "NEUTRAL"
                    if trend == "MARGIN_EXPANSION":
                        severity = "POSITIVE"
                    elif trend == "MARGIN_COMPRESSION":
                        severity = "NEGATIVE"

                    code = f"{m_name}_CHANGE_{comp_type}"
                    expl = f"{m_name.replace('_', ' ').title()} changed by {fmt_pct(diff)} {comp_type} (from {fmt_pct(Decimal(str(comp.previous_value)))} to {fmt_pct(Decimal(str(comp.current_value)))})."

                    signals.append(
                        GeneratedSignal(
                            signal_type="PROFITABILITY",
                            signal_code=code,
                            metric_name=m_name,
                            value=diff,
                            classification=trend,
                            severity=severity,
                            supporting_metric_ids=[comp.metric_id],
                            explanation=expl,
                        )
                    )

            # Debt Change
            elif m_name == "TOTAL_DEBT":
                if comp.percentage_change is not None:
                    pct = Decimal(str(comp.percentage_change))
                    trend = self.classifier.classify_debt_change(pct)

                    severity = "NEUTRAL"
                    if trend == "DEBT_REDUCTION":
                        severity = "POSITIVE"
                    elif trend == "DEBT_INCREASE":
                        severity = "NEGATIVE"

                    code = f"DEBT_CHANGE_{comp_type}"
                    expl = f"Total Debt changed by {fmt_pct(pct)} {comp_type} (from {fmt_val(Decimal(str(comp.previous_value)))} to {fmt_val(Decimal(str(comp.current_value)))})."

                    signals.append(
                        GeneratedSignal(
                            signal_type="LEVERAGE",
                            signal_code=code,
                            metric_name=m_name,
                            value=pct,
                            classification=trend,
                            severity=severity,
                            supporting_metric_ids=[comp.metric_id],
                            explanation=expl,
                        )
                    )

        # 2. Leverage Signals (Debt-to-Revenue change)
        for c_type in ("YOY", "QOQ"):
            debt_comp = comp_by_key.get(("TOTAL_DEBT", c_type))
            rev_comp = comp_by_key.get(("REVENUE", c_type))

            if debt_comp is not None and rev_comp is not None:
                d_prev = Decimal(str(debt_comp.previous_value))
                r_prev = Decimal(str(rev_comp.previous_value))
                d_curr = Decimal(str(debt_comp.current_value))
                r_curr = Decimal(str(rev_comp.current_value))

                if r_prev != Decimal("0") and r_curr != Decimal("0"):
                    prev_ratio = d_prev / r_prev
                    curr_ratio = d_curr / r_curr
                    ratio_diff = curr_ratio - prev_ratio

                    if curr_ratio < prev_ratio:
                        code = f"LEVERAGE_IMPROVEMENT_{c_type}"
                        class_name = "LEVERAGE_IMPROVEMENT"
                        severity = "POSITIVE"
                        expl = f"Debt-to-Revenue ratio improved from {prev_ratio:.4f} to {curr_ratio:.4f} ({c_type})."
                    elif curr_ratio > prev_ratio:
                        code = f"LEVERAGE_DETERIORATION_{c_type}"
                        class_name = "LEVERAGE_DETERIORATION"
                        severity = "NEGATIVE"
                        expl = f"Debt-to-Revenue ratio deteriorated from {prev_ratio:.4f} to {curr_ratio:.4f} ({c_type})."
                    else:
                        code = f"LEVERAGE_UNCHANGED_{c_type}"
                        class_name = "LEVERAGE_UNCHANGED"
                        severity = "NEUTRAL"
                        expl = f"Debt-to-Revenue ratio remained unchanged at {curr_ratio:.4f} ({c_type})."

                    signals.append(
                        GeneratedSignal(
                            signal_type="LEVERAGE",
                            signal_code=code,
                            metric_name="DEBT_TO_REVENUE",
                            value=ratio_diff,
                            classification=class_name,
                            severity=severity,
                            supporting_metric_ids=[debt_comp.metric_id, rev_comp.metric_id],
                            explanation=expl,
                        )
                    )

        # 3. Cash Flow/Generation Signals
        for c_type in ("YOY", "QOQ"):
            fcf_comp = comp_by_key.get(("FREE_CASH_FLOW", c_type))
            if fcf_comp is not None and fcf_comp.percentage_change is not None:
                pct = Decimal(str(fcf_comp.percentage_change))
                if pct > Decimal("0"):
                    signals.append(
                        GeneratedSignal(
                            signal_type="CASH_FLOW",
                            signal_code=f"CASH_GENERATION_IMPROVEMENT_{c_type}",
                            metric_name="FREE_CASH_FLOW",
                            value=pct,
                            classification="CASH_GENERATION_IMPROVEMENT",
                            severity="POSITIVE",
                            supporting_metric_ids=[fcf_comp.metric_id],
                            explanation=f"Free Cash Flow grew by {fmt_pct(pct)} {c_type}, indicating cash generation improvement.",
                        )
                    )
                elif pct < Decimal("0"):
                    signals.append(
                        GeneratedSignal(
                            signal_type="CASH_FLOW",
                            signal_code=f"CASH_FLOW_DETERIORATION_{c_type}",
                            metric_name="FREE_CASH_FLOW",
                            value=pct,
                            classification="CASH_FLOW_DETERIORATION",
                            severity="NEGATIVE",
                            supporting_metric_ids=[fcf_comp.metric_id],
                            explanation=f"Free Cash Flow decreased by {fmt_pct(pct)} {c_type}, indicating cash flow deterioration.",
                        )
                    )

        # 4. Guidance Signals
        # Compare current report's REVENUE_GUIDANCE to previous report's REVENUE_GUIDANCE if available
        rev_guidance = metric_by_name.get("REVENUE_GUIDANCE")
        if rev_guidance is not None and rev_guidance.value is not None:
            # Let's search company_historical_metrics for prior guidance if provided
            prev_guidance = None
            if company_historical_metrics:
                # filter for REVENUE_GUIDANCE from reports with older uploaded_at or different IDs
                guidances = [
                    m for m in company_historical_metrics
                    if m.normalized_metric_name == "REVENUE_GUIDANCE" and m.report_id != rev_guidance.report_id
                ]
                if guidances:
                    # use the most recent one (we assume sorted or we can just pick one)
                    prev_guidance = guidances[0]

            curr_val = Decimal(str(rev_guidance.value))
            if prev_guidance is not None and prev_guidance.value is not None:
                prev_val = Decimal(str(prev_guidance.value))
                if curr_val > prev_val:
                    signals.append(
                        GeneratedSignal(
                            signal_type="GUIDANCE",
                            signal_code="GUIDANCE_RAISED",
                            metric_name="REVENUE_GUIDANCE",
                            value=curr_val - prev_val,
                            classification="GUIDANCE_RAISED",
                            severity="VERY_POSITIVE",
                            supporting_metric_ids=[rev_guidance.id, prev_guidance.id],
                            explanation=f"Revenue Guidance raised from {fmt_val(prev_val)} to {fmt_val(curr_val)}.",
                        )
                    )
                elif curr_val < prev_val:
                    signals.append(
                        GeneratedSignal(
                            signal_type="GUIDANCE",
                            signal_code="GUIDANCE_LOWERED",
                            metric_name="REVENUE_GUIDANCE",
                            value=curr_val - prev_val,
                            classification="GUIDANCE_LOWERED",
                            severity="VERY_NEGATIVE",
                            supporting_metric_ids=[rev_guidance.id, prev_guidance.id],
                            explanation=f"Revenue Guidance lowered from {fmt_val(prev_val)} to {fmt_val(curr_val)}.",
                        )
                    )
                else:
                    signals.append(
                        GeneratedSignal(
                            signal_type="GUIDANCE",
                            signal_code="GUIDANCE_MAINTAINED",
                            metric_name="REVENUE_GUIDANCE",
                            value=Decimal("0"),
                            classification="GUIDANCE_MAINTAINED",
                            severity="NEUTRAL",
                            supporting_metric_ids=[rev_guidance.id, prev_guidance.id],
                            explanation=f"Revenue Guidance maintained at {fmt_val(curr_val)}.",
                        )
                    )
            else:
                # Compare to actual revenue if no prior guidance exists
                actual_rev = metric_by_name.get("REVENUE")
                if actual_rev is not None and actual_rev.value is not None:
                    act_val = Decimal(str(actual_rev.value))
                    diff = curr_val - act_val
                    if curr_val > act_val:
                        signals.append(
                            GeneratedSignal(
                                signal_type="GUIDANCE",
                                signal_code="GUIDANCE_ABOVE_ACTUAL",
                                metric_name="REVENUE_GUIDANCE",
                                value=diff,
                                classification="GUIDANCE_ABOVE_ACTUAL",
                                severity="POSITIVE",
                                supporting_metric_ids=[rev_guidance.id, actual_rev.id],
                                explanation=f"Revenue Guidance of {fmt_val(curr_val)} is above current actual revenue of {fmt_val(act_val)}.",
                            )
                        )
                    else:
                        signals.append(
                            GeneratedSignal(
                                signal_type="GUIDANCE",
                                signal_code="GUIDANCE_BELOW_ACTUAL",
                                metric_name="REVENUE_GUIDANCE",
                                value=diff,
                                classification="GUIDANCE_BELOW_ACTUAL",
                                severity="NEGATIVE",
                                supporting_metric_ids=[rev_guidance.id, actual_rev.id],
                                explanation=f"Revenue Guidance of {fmt_val(curr_val)} is below current actual revenue of {fmt_val(act_val)}.",
                            )
                        )

        # Do the same for MARGIN_GUIDANCE
        margin_guidance = metric_by_name.get("MARGIN_GUIDANCE")
        if margin_guidance is not None and margin_guidance.value is not None:
            prev_m_guidance = None
            if company_historical_metrics:
                m_guidances = [
                    m for m in company_historical_metrics
                    if m.normalized_metric_name == "MARGIN_GUIDANCE" and m.report_id != margin_guidance.report_id
                ]
                if m_guidances:
                    prev_m_guidance = m_guidances[0]

            curr_val = Decimal(str(margin_guidance.value))
            if prev_m_guidance is not None and prev_m_guidance.value is not None:
                prev_val = Decimal(str(prev_m_guidance.value))
                if curr_val > prev_val:
                    signals.append(
                        GeneratedSignal(
                            signal_type="GUIDANCE",
                            signal_code="MARGIN_GUIDANCE_RAISED",
                            metric_name="MARGIN_GUIDANCE",
                            value=curr_val - prev_val,
                            classification="GUIDANCE_RAISED",
                            severity="VERY_POSITIVE",
                            supporting_metric_ids=[margin_guidance.id, prev_m_guidance.id],
                            explanation=f"Margin Guidance raised from {fmt_pct(prev_val)} to {fmt_pct(curr_val)}.",
                        )
                    )
                elif curr_val < prev_val:
                    signals.append(
                        GeneratedSignal(
                            signal_type="GUIDANCE",
                            signal_code="MARGIN_GUIDANCE_LOWERED",
                            metric_name="MARGIN_GUIDANCE",
                            value=curr_val - prev_val,
                            classification="GUIDANCE_LOWERED",
                            severity="VERY_NEGATIVE",
                            supporting_metric_ids=[margin_guidance.id, prev_m_guidance.id],
                            explanation=f"Margin Guidance lowered from {fmt_pct(prev_val)} to {fmt_pct(curr_val)}.",
                        )
                    )
                else:
                    signals.append(
                        GeneratedSignal(
                            signal_type="GUIDANCE",
                            signal_code="MARGIN_GUIDANCE_MAINTAINED",
                            metric_name="MARGIN_GUIDANCE",
                            value=Decimal("0"),
                            classification="GUIDANCE_MAINTAINED",
                            severity="NEUTRAL",
                            supporting_metric_ids=[margin_guidance.id, prev_m_guidance.id],
                            explanation=f"Margin Guidance maintained at {fmt_pct(curr_val)}.",
                        )
                    )

        return signals
