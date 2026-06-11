"""Analytics Builder — orchestrates ratio and signal generation (Phase 3C)."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import List, Dict, Any

from app.models.financial_metric import FinancialMetric
from app.models.metric_comparison import MetricComparison
from app.financial.analytics.analytics_models import CalculatedRatio, GeneratedSignal
from app.financial.analytics.ratio_calculator import RatioCalculator
from app.financial.analytics.trend_classifier import TrendClassifier
from app.financial.analytics.signal_generator import SignalGenerator
from app.financial.analytics.analytics_validator import AnalyticsValidator


class AnalyticsBuilder:
    """Orchestrates ratio calculation, trend classification, signal generation, and validation."""

    def __init__(
        self,
        ratio_calculator: RatioCalculator | None = None,
        signal_generator: SignalGenerator | None = None,
        validator: AnalyticsValidator | None = None,
    ) -> None:
        self.ratio_calculator = ratio_calculator or RatioCalculator()
        self.signal_generator = signal_generator or SignalGenerator()
        self.validator = validator or AnalyticsValidator()

    def build_analytics(
        self,
        company_id: uuid.UUID,
        report_id: uuid.UUID,
        metrics: list[FinancialMetric],
        comparisons: list[MetricComparison],
        company_historical_metrics: list[FinancialMetric] = None,
    ) -> tuple[list[dict[str, Any]], list[str]]:
        # 1. Calculate ratios
        ratios = self.ratio_calculator.calculate_ratios(metrics)

        # 2. Generate signals
        signals = self.signal_generator.generate_signals(
            metrics, comparisons, ratios, company_historical_metrics
        )

        # 3. Validate
        valid_ratios, valid_signals, warnings = self.validator.validate(ratios, signals)

        # 4. Format for DB
        db_rows: list[dict[str, Any]] = []

        # Format Ratios
        for r in valid_ratios:
            # Map ratio code to type
            if r.name in ("GROSS_MARGIN", "OPERATING_MARGIN", "NET_MARGIN"):
                sig_type = "PROFITABILITY"
            elif r.name == "DEBT_TO_REVENUE":
                sig_type = "LEVERAGE"
            elif r.name == "CASH_FLOW_MARGIN":
                sig_type = "CASH_FLOW"
            else:
                sig_type = "GENERAL"

            # Format explanation
            if r.name in ("GROSS_MARGIN", "OPERATING_MARGIN", "NET_MARGIN", "CASH_FLOW_MARGIN"):
                expl = f"{r.name.replace('_', ' ').title()} is {r.value * Decimal('100'):.2f}%"
            else:
                expl = f"{r.name.replace('_', ' ').title()} is {r.value:.4f}"

            db_rows.append(
                {
                    "company_id": company_id,
                    "report_id": report_id,
                    "metric_name": r.name,
                    "signal_type": sig_type,
                    "signal_code": r.name,
                    "value": r.value,
                    "classification": "RATIO",
                    "severity": "NEUTRAL",
                    "supporting_metric_ids": r.supporting_metric_ids,
                    "explanation": expl,
                }
            )

        # Format Signals
        for s in valid_signals:
            db_rows.append(
                {
                    "company_id": company_id,
                    "report_id": report_id,
                    "metric_name": s.metric_name,
                    "signal_type": s.signal_type,
                    "signal_code": s.signal_code,
                    "value": s.value,
                    "classification": s.classification,
                    "severity": s.severity,
                    "supporting_metric_ids": s.supporting_metric_ids,
                    "explanation": s.explanation,
                }
            )

        return db_rows, warnings
