"""RiskFactor ORM model — a structured, extracted risk from financial disclosures (Phase 4).

Risks are extracted from Risk Factors, MD&A, Forward-Looking Statements, and
Guidance sections via hybrid extraction (rule + LLM, cross-validated). Every risk
retains `source_chunk_id` + `source_text` for auditability and future citations.
The LLM may assist extraction but the database is the source of truth — every risk
passes deterministic validation before storage.
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
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import UUIDMixin

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.report import Report


class RiskFactor(UUIDMixin, Base):
    __tablename__ = "risk_factors"

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
    # Traceability: the chunk a risk was read from (SET NULL so re-chunking is safe).
    source_chunk_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("document_chunks.id", ondelete="SET NULL"),
        nullable=True,
    )

    risk_name: Mapped[str] = mapped_column(Text, nullable=False)             # as found in text
    normalized_risk_name: Mapped[str] = mapped_column(String(128), nullable=False)  # canonical
    risk_description: Mapped[str] = mapped_column(Text, nullable=False)

    category: Mapped[str] = mapped_column(String(20), nullable=False)
    severity: Mapped[str] = mapped_column(String(10), nullable=False)

    confidence_score: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False)
    extraction_method: Mapped[str] = mapped_column(String(20), nullable=False)
    source_text: Mapped[str] = mapped_column(Text, nullable=False)

    # Optional provenance / discrepancy flags.
    extraction_metadata: Mapped[dict[str, Any]] = mapped_column(
        "extraction_metadata", JSONB, nullable=False, default=dict
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    company: Mapped["Company"] = relationship()
    report: Mapped["Report"] = relationship()

    __table_args__ = (
        CheckConstraint("confidence_score BETWEEN 0 AND 1", name="ck_risk_factors_confidence"),
        CheckConstraint(
            "category IN ('SUPPLY_CHAIN','REGULATORY','MARKET','COMPETITION','TECHNOLOGY',"
            "'CYBERSECURITY','OPERATIONAL','LIQUIDITY','GEOPOLITICAL','LEGAL',"
            "'ENVIRONMENTAL','REPUTATION','MACROECONOMIC','OTHER')",
            name="ck_risk_factors_category",
        ),
        CheckConstraint(
            "severity IN ('LOW','MEDIUM','HIGH','CRITICAL')",
            name="ck_risk_factors_severity",
        ),
        CheckConstraint(
            "extraction_method IN ('RULE_BASED','LLM_BASED','HYBRID_VALIDATED')",
            name="ck_risk_factors_method",
        ),
        Index("ix_risk_factors_company_id", "company_id"),
        Index("ix_risk_factors_report_id", "report_id"),
        Index("ix_risk_factors_source_chunk_id", "source_chunk_id"),
        Index("ix_risk_factors_category", "category"),
        Index("ix_risk_factors_severity", "severity"),
        Index("ix_risk_factors_company_category", "company_id", "category"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<RiskFactor {self.normalized_risk_name} category={self.category} "
            f"severity={self.severity} report={self.report_id}>"
        )
