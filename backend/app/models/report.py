"""Report ORM model — one uploaded financial document (Phase 1A)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    func,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import UUIDMixin
from app.models.enums import ReportStatus, ReportType

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.document_chunk import DocumentChunk
    from app.models.financial_metric import FinancialMetric
    from app.models.report_page import ReportPage
    from app.models.report_section import ReportSection


class Report(UUIDMixin, Base):
    __tablename__ = "reports"

    company_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=True,
    )

    # Enums stored as VARCHAR + CHECK (native_enum=False) — no PG ENUM type, so
    # values evolve via simple migrations (see docs/02_DATABASE_DESIGN.md §3).
    report_type: Mapped[ReportType] = mapped_column(
        SQLEnum(ReportType, native_enum=False, length=16, name="report_type", validate_strings=True),
        nullable=False,
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    quarter: Mapped[int | None] = mapped_column(Integer, nullable=True)

    original_filename: Mapped[str] = mapped_column(Text, nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    file_data: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)

    status: Mapped[ReportStatus] = mapped_column(
        SQLEnum(
            ReportStatus, native_enum=False, length=32, name="report_status", validate_strings=True
        ),
        nullable=False,
        default=ReportStatus.UPLOADED,
        server_default=ReportStatus.UPLOADED.value,
    )
    total_pages: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Metadata for fully automated event-driven pipeline
    failed_stage: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_stage: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    @property
    def progress(self) -> int:
        """Calculate the completion percentage of the ingestion & extraction pipeline."""
        progress_map = {
            ReportStatus.UPLOADED: 10,
            ReportStatus.PROCESSING: 20,
            ReportStatus.PROCESSED: 20,
            ReportStatus.SECTIONING: 30,
            ReportStatus.SECTIONED: 30,
            ReportStatus.CHUNKING: 40,
            ReportStatus.CHUNKED: 40,
            ReportStatus.EMBEDDING: 55,
            ReportStatus.EMBEDDED: 55,
            "METRICS_EXTRACTING": 65,
            "METRICS_READY": 65,
            "COMPARING": 70,
            "COMPARISON_READY": 70,
            "ANALYTICS": 75,
            "ANALYTICS_READY": 75,
            "RISKS": 85,
            "RISKS_READY": 85,
            "TONE": 92,
            "READY": 100,
        }
        
        # Map the Enum members (which may resolve to original/new values)
        progress_map[ReportStatus.EXTRACTING] = 65
        progress_map[ReportStatus.EXTRACTED] = 65
        progress_map[ReportStatus.COMPARING] = 70
        progress_map[ReportStatus.COMPARED] = 70
        progress_map[ReportStatus.ANALYZING] = 75
        progress_map[ReportStatus.ANALYZED] = 75
        progress_map[ReportStatus.RISK_EXTRACTING] = 85
        progress_map[ReportStatus.RISK_EXTRACTED] = 85
        progress_map[ReportStatus.TONE_EXTRACTING] = 92
        progress_map[ReportStatus.TONE_EXTRACTED] = 100

        current_status = self.status
        if current_status == ReportStatus.FAILED:
            if not self.completed_stage:
                return 0
            stage_to_status = {
                "PROCESSED": ReportStatus.PROCESSED,
                "SECTIONED": ReportStatus.SECTIONED,
                "CHUNKED": ReportStatus.CHUNKED,
                "EMBEDDED": ReportStatus.EMBEDDED,
                "METRICS_READY": ReportStatus.METRICS_READY,
                "COMPARISON_READY": ReportStatus.COMPARISON_READY,
                "ANALYTICS_READY": ReportStatus.ANALYTICS_READY,
                "RISKS_READY": ReportStatus.RISKS_READY,
                "READY": ReportStatus.READY,
            }
            mapped_status = stage_to_status.get(self.completed_stage)
            if mapped_status:
                return progress_map.get(mapped_status, 0)
            return 0
            
        return progress_map.get(current_status, 0)

    processing_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    processing_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    company: Mapped["Company | None"] = relationship(back_populates="reports")
    pages: Mapped[list["ReportPage"]] = relationship(
        back_populates="report",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ReportPage.page_number",
    )
    sections: Mapped[list["ReportSection"]] = relationship(
        back_populates="report",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ReportSection.start_page",
    )
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="report",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="DocumentChunk.chunk_index",
    )
    metrics: Mapped[list["FinancialMetric"]] = relationship(
        back_populates="report",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        CheckConstraint("quarter IS NULL OR (quarter BETWEEN 1 AND 4)", name="quarter_range"),
        CheckConstraint("year BETWEEN 1900 AND 2200", name="year_range"),
        CheckConstraint("total_pages IS NULL OR total_pages >= 0", name="total_pages_nonneg"),
        Index("ix_reports_company_id", "company_id"),
        Index("ix_reports_status", "status"),
        Index("ix_reports_uploaded_at", "uploaded_at"),
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Report id={self.id} type={self.report_type} status={self.status}>"
