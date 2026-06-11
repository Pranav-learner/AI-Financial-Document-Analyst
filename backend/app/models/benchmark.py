"""SQLAlchemy ORM models for Competitor Benchmarking Engine (Phase 8)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import UUIDMixin
from app.models.enums import BenchmarkDimension, BenchmarkStatus

if TYPE_CHECKING:
    from app.models.company import Company


class BenchmarkRun(UUIDMixin, Base):
    __tablename__ = "benchmark_runs"

    run_name: Mapped[str] = mapped_column(Text, nullable=False)
    company_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(PG_UUID(as_uuid=True)), nullable=False
    )
    benchmark_type: Mapped[str] = mapped_column(String(50), nullable=False)
    configuration: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    status: Mapped[BenchmarkStatus] = mapped_column(
        SQLEnum(
            BenchmarkStatus,
            native_enum=False,
            length=20,
            name="benchmark_run_status",
            validate_strings=True,
        ),
        nullable=False,
        default=BenchmarkStatus.PENDING,
        server_default=BenchmarkStatus.PENDING.value,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED')",
            name="ck_benchmark_runs_status",
        ),
        Index("ix_benchmark_runs_status", "status"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<BenchmarkRun id={self.id} name={self.run_name!r} status={self.status}>"


class BenchmarkResult(UUIDMixin, Base):
    __tablename__ = "benchmark_results"

    benchmark_run_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("benchmark_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
    )
    benchmark_dimension: Mapped[BenchmarkDimension] = mapped_column(
        SQLEnum(
            BenchmarkDimension,
            native_enum=False,
            length=32,
            name="benchmark_result_dimension",
            validate_strings=True,
        ),
        nullable=False,
    )
    metric_name: Mapped[str] = mapped_column(String(64), nullable=False)
    metric_value: Mapped[Any | None] = mapped_column(Numeric, nullable=True)
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    percentile: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    score: Mapped[float | None] = mapped_column(Numeric, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    company: Mapped["Company"] = relationship()

    __table_args__ = (
        CheckConstraint(
            "benchmark_dimension IN ('FINANCIAL', 'RISK', 'TONE', 'CAPITAL_ALLOCATION', 'OVERALL')",
            name="ck_benchmark_results_dimension",
        ),
        Index("ix_benchmark_results_run", "benchmark_run_id"),
        Index("ix_benchmark_results_company", "company_id"),
        Index("ix_benchmark_results_dimension", "benchmark_dimension"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<BenchmarkResult company={self.company_id} dim={self.benchmark_dimension} "
            f"metric={self.metric_name} score={self.score}>"
        )


class BenchmarkSummary(UUIDMixin, Base):
    __tablename__ = "benchmark_summaries"

    benchmark_run_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("benchmark_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
    )
    financial_score: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    risk_score: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    tone_score: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    capital_allocation_score: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    overall_score: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    company: Mapped["Company"] = relationship()

    __table_args__ = (
        Index("ix_benchmark_summaries_run", "benchmark_run_id"),
        Index("ix_benchmark_summaries_company", "company_id"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<BenchmarkSummary run={self.benchmark_run_id} company={self.company_id} rank={self.rank} score={self.overall_score}>"
