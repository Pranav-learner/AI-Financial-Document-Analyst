"""ReportSection ORM model — a logical section detected within a report (Phase 1B).

Stores the *complete* section content and its page boundaries. This is structured
document intelligence kept separate from any future RAG/vector data (ADR-007).
No chunking here — chunking is Phase 1C.
"""

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
    Numeric,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import UUIDMixin

if TYPE_CHECKING:
    from app.models.document_chunk import DocumentChunk
    from app.models.report import Report


class ReportSection(UUIDMixin, Base):
    __tablename__ = "report_sections"

    report_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=False,
    )
    section_name: Mapped[str] = mapped_column(Text, nullable=False)            # raw heading text
    normalized_section_name: Mapped[str] = mapped_column(Text, nullable=False)  # canonical taxonomy
    start_page: Mapped[int] = mapped_column(Integer, nullable=False)            # 1-based, inclusive
    end_page: Mapped[int] = mapped_column(Integer, nullable=False)             # 1-based, inclusive
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    confidence_score: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    report: Mapped["Report"] = relationship(back_populates="sections")
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="section",
        passive_deletes=True,
        order_by="DocumentChunk.chunk_index",
    )

    __table_args__ = (
        CheckConstraint("confidence_score BETWEEN 0 AND 1", name="ck_report_sections_confidence"),
        CheckConstraint("start_page >= 1", name="ck_report_sections_start_page"),
        CheckConstraint("end_page >= start_page", name="ck_report_sections_page_order"),
        Index("ix_report_sections_report_id", "report_id"),
        Index("ix_report_sections_normalized_name", "normalized_section_name"),
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return (
            f"<ReportSection report_id={self.report_id} "
            f"name={self.normalized_section_name!r} pages={self.start_page}-{self.end_page}>"
        )
