"""Trend Classifier — classifies changes and ratios into trends (Phase 3C)."""

from __future__ import annotations

from decimal import Decimal


class TrendClassifier:
    """Classifies growth rates, margin changes, and debt trends using configurable thresholds."""

    def __init__(self, thresholds: dict[str, float] | None = None) -> None:
        self.thresholds = thresholds or {
            "strong_growth": 0.15,
            "moderate_growth": 0.05,
            "low_growth": 0.00,
        }

    def classify_growth(self, rate: Decimal) -> str:
        strong = Decimal(str(self.thresholds["strong_growth"]))
        mod = Decimal(str(self.thresholds["moderate_growth"]))
        low = Decimal(str(self.thresholds["low_growth"]))

        if rate > strong:
            return "STRONG_GROWTH"
        elif rate >= mod:
            return "MODERATE_GROWTH"
        elif rate >= low:
            return "LOW_GROWTH"
        else:
            return "DECLINING"

    def classify_margin_change(self, absolute_change: Decimal) -> str:
        if absolute_change > Decimal("0"):
            return "MARGIN_EXPANSION"
        elif absolute_change < Decimal("0"):
            return "MARGIN_COMPRESSION"
        else:
            return "MARGIN_UNCHANGED"

    def classify_debt_change(self, pct_change: Decimal) -> str:
        if pct_change < Decimal("0"):
            return "DEBT_REDUCTION"
        elif pct_change > Decimal("0"):
            return "DEBT_INCREASE"
        else:
            return "DEBT_UNCHANGED"
