"""DocumentChunk ORM model — a retrieval-ready knowledge chunk (Phase 1C).

Chunks are produced by section-aware recursive chunking of `report_sections`.
This phase deliberately stores **no embedding / vector column** — embeddings and
the pgvector column are introduced in Phase 2 (see docs/02_DATABASE_DESIGN.md §6.1
and ADR-007: structured data is prepared separately from future RAG vectors).

Note: the JSONB column is named `metadata` in the database, but the Python
attribute is `chunk_metadata` because `metadata` is reserved by SQLAlchemy's
declarative base.
"""

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
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import UUIDMixin

if TYPE_CHECKING:
    from app.models.report import Report
    from app.models.report_section import ReportSection


class DocumentChunk(UUIDMixin, Base):
    __tablename__ = "document_chunks"

    report_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=False,
    )
    section_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("report_sections.id", ondelete="SET NULL"),
        nullable=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)  # 0-based, per report
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    start_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # DB column "metadata"; attribute renamed to avoid SQLAlchemy's reserved name.
    chunk_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    report: Mapped["Report"] = relationship(back_populates="chunks")
    section: Mapped["ReportSection | None"] = relationship(back_populates="chunks")

    __table_args__ = (
        UniqueConstraint("report_id", "chunk_index", name="uq_document_chunks_report_index"),
        CheckConstraint("token_count >= 0", name="ck_document_chunks_token_count"),
        CheckConstraint("chunk_index >= 0", name="ck_document_chunks_index"),
        Index("ix_document_chunks_report_id", "report_id"),
        Index("ix_document_chunks_section_id", "section_id"),
        Index("ix_document_chunks_metadata", "metadata", postgresql_using="gin"),
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return (
            f"<DocumentChunk report_id={self.report_id} "
            f"index={self.chunk_index} tokens={self.token_count}>"
        )
