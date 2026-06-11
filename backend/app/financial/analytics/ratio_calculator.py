"""Ratio Calculator — computes financial ratios from report metrics (Phase 3C)."""

from __future__ import annotations

from decimal import Decimal
import uuid
from typing import List, Dict, Optional

from app.models.financial_metric import FinancialMetric
from app.financial.analytics.analytics_models import CalculatedRatio


class RatioCalculator:
    """Calculates financial ratios deterministically from report metrics."""

    def calculate_ratios(self, metrics: list[FinancialMetric]) -> list[CalculatedRatio]:
        by_name: dict[str, FinancialMetric] = {m.normalized_metric_name: m for m in metrics}
        ratios: list[CalculatedRatio] = []

        rev = by_name.get("REVENUE")

        # Helper to check if value is non-zero
        def is_valid_denominator(m: FinancialMetric | None) -> bool:
            return m is not None and m.value is not None and Decimal(str(m.value)) != Decimal("0")

        # 1. Gross Margin (Gross Profit / Revenue)
        gp = by_name.get("GROSS_PROFIT")
        gm_metric = by_name.get("GROSS_MARGIN")
        if gp is not None and is_valid_denominator(rev):
            ratios.append(
                CalculatedRatio(
                    name="GROSS_MARGIN",
                    value=Decimal(str(gp.value)) / Decimal(str(rev.value)),
                    supporting_metric_ids=[gp.id, rev.id],
                )
            )
        elif gm_metric is not None and gm_metric.value is not None:
            ratios.append(
                CalculatedRatio(
                    name="GROSS_MARGIN",
                    value=Decimal(str(gm_metric.value)),
                    supporting_metric_ids=[gm_metric.id],
                )
            )

        # 2. Operating Margin (Operating Income / Revenue)
        op_inc = by_name.get("OPERATING_INCOME")
        op_marg_metric = by_name.get("OPERATING_MARGIN")
        if op_inc is not None and is_valid_denominator(rev):
            ratios.append(
                CalculatedRatio(
                    name="OPERATING_MARGIN",
                    value=Decimal(str(op_inc.value)) / Decimal(str(rev.value)),
                    supporting_metric_ids=[op_inc.id, rev.id],
                )
            )
        elif op_marg_metric is not None and op_marg_metric.value is not None:
            ratios.append(
                CalculatedRatio(
                    name="OPERATING_MARGIN",
                    value=Decimal(str(op_marg_metric.value)),
                    supporting_metric_ids=[op_marg_metric.id],
                )
            )

        # 3. Net Margin (Net Income / Revenue)
        net_inc = by_name.get("NET_INCOME")
        net_marg_metric = by_name.get("NET_MARGIN")
        if net_inc is not None and is_valid_denominator(rev):
            ratios.append(
                CalculatedRatio(
                    name="NET_MARGIN",
                    value=Decimal(str(net_inc.value)) / Decimal(str(rev.value)),
                    supporting_metric_ids=[net_inc.id, rev.id],
                )
            )
        elif net_marg_metric is not None and net_marg_metric.value is not None:
            ratios.append(
                CalculatedRatio(
                    name="NET_MARGIN",
                    value=Decimal(str(net_marg_metric.value)),
                    supporting_metric_ids=[net_marg_metric.id],
                )
            )

        # 4. Debt-to-Revenue (Total Debt / Revenue)
        debt = by_name.get("TOTAL_DEBT")
        if debt is not None and is_valid_denominator(rev):
            ratios.append(
                CalculatedRatio(
                    name="DEBT_TO_REVENUE",
                    value=Decimal(str(debt.value)) / Decimal(str(rev.value)),
                    supporting_metric_ids=[debt.id, rev.id],
                )
            )

        # 5. Cash Flow Margin (Operating Cash Flow / Revenue)
        ocf = by_name.get("OPERATING_CASH_FLOW")
        if ocf is not None and is_valid_denominator(rev):
            ratios.append(
                CalculatedRatio(
                    name="CASH_FLOW_MARGIN",
                    value=Decimal(str(ocf.value)) / Decimal(str(rev.value)),
                    supporting_metric_ids=[ocf.id, rev.id],
                )
            )

        return ratios
