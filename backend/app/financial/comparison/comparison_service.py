"""Comparison service (Phase 3B, task §6).

Deterministic period-comparison generation:

    current metrics (the report's) + the company's full metric history
        → dedupe by (metric, period)
        → for each current metric, for YOY and QOQ:
              match the previous period → calculate change → validate → collect
        → rows + observability stats

All processing is deterministic (no LLM, no I/O here). The caller supplies the
already-loaded `MetricPoint`s; the Celery task wires the DB.
"""

from __future__ import annotations

import time

from app.core.logging import get_logger
from app.financial.comparison.comparison_builder import build_comparison
from app.financial.comparison.comparison_models import (
    ComparisonResult,
    ComparisonRow,
    ComparisonStats,
    MetricPoint,
)
from app.financial.comparison.comparison_validator import ComparisonValidator
from app.financial.comparison.period_matcher import PeriodMatcher
from app.models.enums import ComparisonType

log = get_logger(__name__)

# Comparison kinds generated in Phase 3B (YTD/TTM are reserved enum values).
_GENERATED_TYPES = (ComparisonType.YOY.value, ComparisonType.QOQ.value)


class ComparisonService:
    def __init__(self, *, validator: ComparisonValidator | None = None) -> None:
        self.validator = validator or ComparisonValidator()

    @staticmethod
    def _index(points: list[MetricPoint]) -> dict[tuple, MetricPoint]:
        """Dedupe by (metric, period), keeping the highest-confidence point."""
        best: dict[tuple, MetricPoint] = {}
        for p in points:
            cur = best.get(p.period_key())
            if cur is None or p.confidence > cur.confidence:
                best[p.period_key()] = p
        return best

    def build_comparisons(
        self, current_points: list[MetricPoint], all_points: list[MetricPoint], company_id: str
    ) -> ComparisonResult:
        started = time.monotonic()
        stats = ComparisonStats()

        history = self._index(all_points)
        current = list(self._index(current_points).values())
        stats.current_metrics = len(current)

        rows: list[ComparisonRow] = []
        seen: set[tuple[str, str]] = set()

        for cp in current:
            covered = False
            for ctype in _GENERATED_TYPES:
                prev = PeriodMatcher.previous_period(ctype, cp.fiscal_year, cp.fiscal_quarter)
                if prev is None:
                    continue  # type not applicable (e.g. QoQ on an annual metric)
                pp = history.get((cp.normalized_metric_name, prev[0], prev[1]))
                if pp is None:
                    stats.missing_periods += 1
                    continue

                row = build_comparison(cp, pp, ctype, company_id)
                vr = self.validator.validate(row, seen=seen)
                if not vr.is_valid:
                    stats.validation_failures += 1
                    if "non_finite_result" in vr.fatal or "non_finite_absolute" in vr.fatal:
                        stats.calculation_errors += 1
                    continue
                seen.add((row.metric_id, ctype))
                rows.append(row)
                stats.comparisons_generated += 1
                covered = True
            if covered:
                stats._covered += 1

        stats.duration_seconds = round(time.monotonic() - started, 4)
        log.info("comparison.run_complete", company_id=company_id, **stats.as_dict())
        return ComparisonResult(rows=rows, stats=stats)
