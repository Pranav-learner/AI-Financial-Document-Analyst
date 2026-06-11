"""SQLAlchemy ORM models for Investment Memo Generation Engine (Phase 9)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import UUIDMixin
from app.models.enums import MemoStatus, MemoType


class InvestmentMemo(UUIDMixin, Base):
    __tablename__ = "investment_memos"

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
    benchmark_run_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("benchmark_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    memo_type: Mapped[MemoType] = mapped_column(
        SQLEnum(
            MemoType,
            native_enum=False,
            length=32,
            name="memo_type_enum",
            validate_strings=True,
        ),
        nullable=False,
    )
    status: Mapped[MemoStatus] = mapped_column(
        SQLEnum(
            MemoStatus,
            native_enum=False,
            length=20,
            name="memo_status_enum",
            validate_strings=True,
        ),
        nullable=False,
        default=MemoStatus.PENDING,
        server_default=MemoStatus.PENDING.value,
    )
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    executive_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_fields: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict, server_default="{}"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    sections: Mapped[list[MemoSection]] = relationship(
        "MemoSection",
        back_populates="memo",
        cascade="all, delete-orphan",
        order_by="MemoSection.section_order",
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING', 'GENERATING', 'COMPLETED', 'FAILED')",
            name="ck_investment_memos_status",
        ),
        CheckConstraint(
            "memo_type IN ('SINGLE_COMPANY', 'BENCHMARK_COMPARISON')",
            name="ck_investment_memos_type",
        ),
        Index("ix_investment_memos_company", "company_id"),
        Index("ix_investment_memos_report", "report_id"),
        Index("ix_investment_memos_status", "status"),
    )


class MemoSection(UUIDMixin, Base):
    __tablename__ = "memo_sections"

    memo_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("investment_memos.id", ondelete="CASCADE"),
        nullable=False,
    )
    section_name: Mapped[str] = mapped_column(String(128), nullable=False)
    section_order: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    citations: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    memo: Mapped[InvestmentMemo] = relationship("InvestmentMemo", back_populates="sections")

    __table_args__ = (
        Index("ix_memo_sections_memo", "memo_id"),
    )
