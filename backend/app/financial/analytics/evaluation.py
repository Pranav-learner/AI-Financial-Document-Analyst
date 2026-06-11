"""Financial Analytics Evaluation (Phase 3C).

Verifies the ratio calculation and signal generation logic against gold scenarios.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from app.models.financial_metric import FinancialMetric
from app.models.metric_comparison import MetricComparison
from app.financial.analytics.analytics_builder import AnalyticsBuilder

_DEFAULT_PATH = Path(__file__).with_name("gold_dataset.json")


@dataclass
class AnalyticsEvaluationReport:
    num_scenarios: int
    total_expected_ratios: int
    matched_ratios: int
    ratio_accuracy: float
    total_expected_signals: int
    matched_signals: int
    signal_coverage: float
    correct_signal_classifications: int
    signal_accuracy: float
    validation_warnings: int

    def as_dict(self) -> dict:
        return asdict(self)


def load_gold_scenarios(path: str | Path | None = None) -> list[dict]:
    p = Path(path) if path else _DEFAULT_PATH
    return json.loads(p.read_text(encoding="utf-8")).get("scenarios", [])


def _to_metric(m: dict, company_id: uuid.UUID, report_id: uuid.UUID) -> FinancialMetric:
    return FinancialMetric(
        id=uuid.uuid4(),
        report_id=report_id,
        metric_name=m["name"],
        normalized_metric_name=m["name"],
        metric_category="OTHER",
        value=Decimal(str(m["value"])),
        unit="USD",
        confidence_score=1.0,
        extraction_method="RULE_BASED",
        source_text="",
    )


def _to_comparison(c: dict, company_id: uuid.UUID, report_id: uuid.UUID) -> MetricComparison:
    return MetricComparison(
        id=uuid.uuid4(),
        metric_id=uuid.uuid4(),
        company_id=company_id,
        metric_name=c["metric_name"],
        comparison_type=c["comparison_type"],
        current_period="2025-Q1",
        previous_period="2024-Q1",
        current_value=Decimal(str(c["current_value"])),
        previous_value=Decimal(str(c["previous_value"])),
        absolute_change=Decimal(str(c["absolute_change"])) if c.get("absolute_change") is not None else None,
        percentage_change=Decimal(str(c["percentage_change"])) if c.get("percentage_change") is not None else None,
    )


class AnalyticsEvaluator:
    def __init__(self, builder: AnalyticsBuilder | None = None) -> None:
        self.builder = builder or AnalyticsBuilder()

    def evaluate(self, scenarios: list[dict]) -> AnalyticsEvaluationReport:
        total_expected_ratios = matched_ratios = 0
        total_expected_signals = matched_signals = correct_signal_classifications = 0
        total_warnings = 0

        for sc in scenarios:
            company_id = uuid.UUID(sc["company_id"])
            report_id = uuid.UUID(sc["report_id"])

            # Map mock inputs
            metrics = [_to_metric(m, company_id, report_id) for m in sc["metrics"]]
            comparisons = [_to_comparison(c, company_id, report_id) for c in sc["comparisons"]]
            historical = [_to_metric(m, company_id, report_id) for m in sc["historical_metrics"]]

            # Run builder
            rows, warnings = self.builder.build_analytics(
                company_id=company_id,
                report_id=report_id,
                metrics=metrics,
                comparisons=comparisons,
                company_historical_metrics=historical,
            )
            total_warnings += len(warnings)

            # Separate produced ratios and signals
            ratios_dict = {
                r["signal_code"]: r for r in rows if r["classification"] == "RATIO"
            }
            signals_dict = {
                s["signal_code"]: s for s in rows if s["classification"] != "RATIO"
            }

            # Evaluate Ratios
            for exp_r in sc.get("expected_ratios", []):
                total_expected_ratios += 1
                name = exp_r["name"]
                val = Decimal(str(exp_r["value"]))
                got = ratios_dict.get(name)
                if got is not None and abs(Decimal(str(got["value"])) - val) < Decimal("0.0001"):
                    matched_ratios += 1

            # Evaluate Signals
            for exp_s in sc.get("expected_signals", []):
                total_expected_signals += 1
                code = exp_s["code"]
                got = signals_dict.get(code)
                if got is not None:
                    matched_signals += 1
                    # Check classification, type, severity, and value
                    cls_ok = got["classification"] == exp_s["classification"]
                    type_ok = got["signal_type"] == exp_s["type"]
                    sev_ok = got["severity"] == exp_s["severity"]
                    val_ok = True
                    if exp_s.get("value") is not None:
                        val_ok = abs(Decimal(str(got["value"])) - Decimal(str(exp_s["value"]))) < Decimal("0.0001")
                    
                    if cls_ok and type_ok and sev_ok and val_ok:
                        correct_signal_classifications += 1

        return AnalyticsEvaluationReport(
            num_scenarios=len(scenarios),
            total_expected_ratios=total_expected_ratios,
            matched_ratios=matched_ratios,
            ratio_accuracy=round(matched_ratios / total_expected_ratios, 4) if total_expected_ratios else 0.0,
            total_expected_signals=total_expected_signals,
            matched_signals=matched_signals,
            signal_coverage=round(matched_signals / total_expected_signals, 4) if total_expected_signals else 0.0,
            correct_signal_classifications=correct_signal_classifications,
            signal_accuracy=round(correct_signal_classifications / matched_signals, 4) if matched_signals else 0.0,
            validation_warnings=total_warnings,
        )


if __name__ == "__main__":
    # Self-runnable script
    scenarios = load_gold_scenarios()
    report = AnalyticsEvaluator().evaluate(scenarios)
    print("Financial Analytics Offline Evaluation Summary:")
    print(json.dumps(report.as_dict(), indent=2))
