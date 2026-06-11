"""Domain models and dataclasses for financial analytics."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional


@dataclass(frozen=True)
class CalculatedRatio:
    """Represents a deterministically calculated financial ratio."""
    name: str  # e.g., GROSS_MARGIN, OPERATING_MARGIN, NET_MARGIN, DEBT_TO_REVENUE, CASH_FLOW_MARGIN
    value: Decimal
    supporting_metric_ids: list[uuid.UUID] = field(default_factory=list)


@dataclass(frozen=True)
class GeneratedSignal:
    """Represents a deterministically generated financial signal/trend."""
    signal_type: str  # GROWTH, PROFITABILITY, LIQUIDITY, LEVERAGE, CASH_FLOW, EFFICIENCY, GUIDANCE, GENERAL
    signal_code: str  # e.g. REVENUE_GROWTH_STRONG, MARGIN_EXPANSION
    metric_name: Optional[str]  # e.g. REVENUE, OPERATING_MARGIN (or None if multi-metric)
    value: Optional[Decimal]  # e.g. growth rate, absolute margin change
    classification: str  # e.g. STRONG_GROWTH, MARGIN_EXPANSION
    severity: str  # VERY_POSITIVE, POSITIVE, NEUTRAL, NEGATIVE, VERY_NEGATIVE
    supporting_metric_ids: list[uuid.UUID] = field(default_factory=list)
    explanation: str = ""
