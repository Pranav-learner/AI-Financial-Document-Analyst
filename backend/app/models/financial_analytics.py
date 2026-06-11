"""FinancialAnalytics ORM model — a deterministic signal, ratio, or classification (Phase 3C)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import UUIDMixin

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.report import Report


class FinancialAnalytics(UUIDMixin, Base):
    __tablename__ = "financial_analytics"

    company_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
    )
    report_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=False,
    )
    metric_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    signal_type: Mapped[str] = mapped_column(String(20), nullable=False)
    signal_code: Mapped[str] = mapped_column(String(64), nullable=False)
    value: Mapped[Any | None] = mapped_column(Numeric, nullable=True)
    classification: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    supporting_metric_ids: Mapped[list[uuid.UUID] | None] = mapped_column(
        ARRAY(PG_UUID(as_uuid=True)), nullable=True
    )
    explanation: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    company: Mapped["Company"] = relationship()
    report: Mapped["Report"] = relationship()

    __table_args__ = (
        CheckConstraint(
            "signal_type IN ('GROWTH', 'PROFITABILITY', 'LIQUIDITY', 'LEVERAGE', 'CASH_FLOW', 'EFFICIENCY', 'GUIDANCE', 'GENERAL')",
            name="ck_financial_analytics_type",
        ),
        CheckConstraint(
            "severity IN ('VERY_POSITIVE', 'POSITIVE', 'NEUTRAL', 'NEGATIVE', 'VERY_NEGATIVE')",
            name="ck_financial_analytics_severity",
        ),
        Index("ix_financial_analytics_company_id", "company_id"),
        Index("ix_financial_analytics_report_id", "report_id"),
        Index("ix_financial_analytics_company_type", "company_id", "signal_type"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<FinancialAnalytics {self.signal_code} type={self.signal_type} "
            f"severity={self.severity} value={self.value}>"
        )
