"""Analytics Validator — validates calculated ratios and generated signals (Phase 3C)."""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import List, Tuple

from app.financial.analytics.analytics_models import CalculatedRatio, GeneratedSignal

logger = logging.getLogger(__name__)


class AnalyticsValidator:
    """Validates financial ratios and signals to detect anomalies, impossible ratios, and duplicates."""

    def validate(
        self, ratios: list[CalculatedRatio], signals: list[GeneratedSignal]
    ) -> tuple[list[CalculatedRatio], list[GeneratedSignal], list[str]]:
        valid_ratios: list[CalculatedRatio] = []
        valid_signals: list[GeneratedSignal] = []
        warnings: list[str] = []

        # 1. Validate Ratios
        for r in ratios:
            # Check for impossible ratios
            if abs(r.value) > Decimal("20.0"):
                warn = f"Impossible ratio value for {r.name}: {r.value:.4f} (absolute value > 20)"
                logger.warning(warn)
                warnings.append(warn)
                continue

            # Check Gross Margin specific constraints (usually Gross Margin is <= 1.0 under normal circumstances)
            if r.name == "GROSS_MARGIN" and r.value > Decimal("1.0"):
                warn = f"Gross Margin is greater than 100%: {r.value * Decimal('100'):.2f}%"
                logger.warning(warn)
                warnings.append(warn)

            valid_ratios.append(r)

        # 2. Validate Signals (Detect Duplicates and invalid severities)
        seen_codes: set[tuple[str, str | None]] = set()
        for s in signals:
            # Check for duplicate signals
            key = (s.signal_code, s.metric_name)
            if key in seen_codes:
                warn = f"Duplicate signal detected and skipped: code={s.signal_code}, metric={s.metric_name}"
                logger.warning(warn)
                warnings.append(warn)
                continue

            # Check for severity validity
            if s.severity not in ("VERY_POSITIVE", "POSITIVE", "NEUTRAL", "NEGATIVE", "VERY_NEGATIVE"):
                warn = f"Invalid severity level for signal {s.signal_code}: {s.severity}"
                logger.warning(warn)
                warnings.append(warn)
                continue

            seen_codes.add(key)
            valid_signals.append(s)

        return valid_ratios, valid_signals, warnings
