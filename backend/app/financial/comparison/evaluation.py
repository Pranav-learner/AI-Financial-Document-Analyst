"""Comparison evaluation (Phase 3B, task §12).

Verifies the engine against a gold set of scenarios (company history + current
period + expected comparisons with exact deltas). Metrics:

  * **period_matching_accuracy**: expected comparisons that were produced (right
    metric + type + matched periods) / total expected.
  * **calculation_accuracy**: of those produced, fraction with exactly-correct
    absolute AND percentage change.
  * **comparison_coverage**: produced-matching / total expected (engine found the
    pairs it should).
  * **validation_failure_rate**: validation failures / comparisons attempted.

Deterministic — no LLM, no I/O.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path

from app.core.config import settings
from app.financial.comparison.comparison_models import MetricPoint
from app.financial.comparison.comparison_service import ComparisonService

_DEFAULT_PATH = Path(__file__).with_name("gold_dataset.json")


@dataclass
class ComparisonEvaluationReport:
    num_scenarios: int
    total_expected: int
    produced_matching: int
    calculation_correct: int
    period_matching_accuracy: float
    calculation_accuracy: float
    comparison_coverage: float
    validation_failure_rate: float

    def as_dict(self) -> dict:
        return asdict(self)


def _dec(v) -> Decimal | None:
    return None if v is None else Decimal(str(v))


def load_gold_scenarios(path: str | Path | None = None) -> list[dict]:
    p = Path(path) if path else (
        Path(settings.comparison_gold_path) if settings.comparison_gold_path else _DEFAULT_PATH
    )
    return json.loads(p.read_text(encoding="utf-8")).get("scenarios", [])


def _points(raw: list[dict]) -> list[MetricPoint]:
    return [
        MetricPoint(
            metric_id=f"{r['metric']}-{r['year']}-{r.get('quarter')}",
            normalized_metric_name=r["metric"],
            value=Decimal(str(r["value"])),
            fiscal_year=r["year"],
            fiscal_quarter=r.get("quarter"),
        )
        for r in raw
    ]


class ComparisonEvaluator:
    def __init__(self, *, service: ComparisonService | None = None) -> None:
        self.service = service or ComparisonService()

    def evaluate(self, scenarios: list[dict]) -> ComparisonEvaluationReport:
        total_expected = produced_matching = calc_correct = 0
        attempted = validation_failures = 0

        for sc in scenarios:
            points = _points(sc["points"])
            cur = sc["current"]
            current_points = [
                p for p in points
                if p.fiscal_year == cur["year"] and p.fiscal_quarter == cur.get("quarter")
            ]
            result = self.service.build_comparisons(current_points, points, sc.get("id", "c"))
            attempted += result.stats.comparisons_generated + result.stats.validation_failures
            validation_failures += result.stats.validation_failures

            produced = {
                (r.metric_name, r.comparison_type): r for r in result.rows
            }
            for exp in sc["expected"]:
                total_expected += 1
                got = produced.get((exp["metric"], exp["type"]))
                if got is None:
                    continue
                if got.previous_period != exp["previous_period"] or got.current_period != exp["current_period"]:
                    continue
                produced_matching += 1
                abs_ok = got.absolute_change == _dec(exp["absolute_change"])
                pct_ok = got.percentage_change == _dec(exp["percentage_change"])
                if abs_ok and pct_ok:
                    calc_correct += 1

        return ComparisonEvaluationReport(
            num_scenarios=len(scenarios),
            total_expected=total_expected,
            produced_matching=produced_matching,
            calculation_correct=calc_correct,
            period_matching_accuracy=round(produced_matching / total_expected, 4) if total_expected else 0.0,
            calculation_accuracy=round(calc_correct / produced_matching, 4) if produced_matching else 0.0,
            comparison_coverage=round(produced_matching / total_expected, 4) if total_expected else 0.0,
            validation_failure_rate=round(validation_failures / attempted, 4) if attempted else 0.0,
        )
