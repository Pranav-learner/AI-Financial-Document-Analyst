"""MetricComparison ORM model — a deterministic period-over-period comparison (Phase 3B).

Stores YoY/QoQ deltas computed by **deterministic formulas over stored metric
values** (ADR-007/ADR-018) — never by an LLM. Each row links the *current*-period
metric (`metric_id`) and records the matched previous period's value plus the
absolute and percentage change.

`current_value` / `previous_value` are the normalized ABSOLUTE magnitudes from
`financial_metrics` (same scale). `percentage_change` is NULL when it cannot be
computed deterministically (e.g. previous value is 0 or missing).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy import CheckConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import UUIDMixin

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.financial_metric import FinancialMetric


class MetricComparison(UUIDMixin, Base):
    __tablename__ = "metric_comparisons"

    # The CURRENT-period metric this comparison is anchored to.
    metric_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("financial_metrics.id", ondelete="CASCADE"),
        nullable=False,
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
    )
    metric_name: Mapped[str] = mapped_column(String(64), nullable=False)   # normalized
    comparison_type: Mapped[str] = mapped_column(String(8), nullable=False)  # YOY/QOQ/YTD/TTM

    current_period: Mapped[str] = mapped_column(String(16), nullable=False)   # e.g. FY2024 / Q1 2025
    previous_period: Mapped[str] = mapped_column(String(16), nullable=False)

    current_value: Mapped[Any] = mapped_column(Numeric, nullable=False)
    previous_value: Mapped[Any] = mapped_column(Numeric, nullable=False)
    absolute_change: Mapped[Any | None] = mapped_column(Numeric, nullable=True)
    percentage_change: Mapped[Any | None] = mapped_column(Numeric, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    metric: Mapped["FinancialMetric"] = relationship()
    company: Mapped["Company"] = relationship()

    __table_args__ = (
        UniqueConstraint("metric_id", "comparison_type", name="uq_metric_comparisons_metric_type"),
        CheckConstraint(
            "comparison_type IN ('YOY','QOQ','YTD','TTM')",
            name="ck_metric_comparisons_type",
        ),
        Index("ix_metric_comparisons_company_id", "company_id"),
        Index("ix_metric_comparisons_metric_id", "metric_id"),
        Index("ix_metric_comparisons_company_metric", "company_id", "metric_name"),
        Index("ix_metric_comparisons_type", "comparison_type"),
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return (
            f"<MetricComparison {self.metric_name} {self.comparison_type} "
            f"{self.previous_period}->{self.current_period} Δ%={self.percentage_change}>"
        )
