"""RiskEvolution ORM model — period-over-period risk changes (Phase 4).

Tracks how risks evolve across reporting periods: NEW_RISK, REMOVED_RISK,
UNCHANGED_RISK, ESCALATED_RISK, REDUCED_RISK. Deterministic — the LLM is not
involved in evolution classification (it's pure severity-delta logic).
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
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import UUIDMixin

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.risk_factor import RiskFactor


class RiskEvolution(UUIDMixin, Base):
    __tablename__ = "risk_evolution"

    company_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
    )
    current_risk_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("risk_factors.id", ondelete="CASCADE"),
        nullable=True,  # NULL for REMOVED_RISK (previous exists, current does not)
    )
    previous_risk_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("risk_factors.id", ondelete="CASCADE"),
        nullable=True,  # NULL for NEW_RISK (current exists, previous does not)
    )

    evolution_type: Mapped[str] = mapped_column(String(20), nullable=False)
    confidence_score: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    company: Mapped["Company"] = relationship()
    current_risk: Mapped["RiskFactor | None"] = relationship(foreign_keys=[current_risk_id])
    previous_risk: Mapped["RiskFactor | None"] = relationship(foreign_keys=[previous_risk_id])

    __table_args__ = (
        CheckConstraint("confidence_score BETWEEN 0 AND 1", name="ck_risk_evolution_confidence"),
        CheckConstraint(
            "evolution_type IN ('NEW_RISK','REMOVED_RISK','UNCHANGED_RISK',"
            "'ESCALATED_RISK','REDUCED_RISK')",
            name="ck_risk_evolution_type",
        ),
        Index("ix_risk_evolution_company_id", "company_id"),
        Index("ix_risk_evolution_current_risk_id", "current_risk_id"),
        Index("ix_risk_evolution_previous_risk_id", "previous_risk_id"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<RiskEvolution type={self.evolution_type} "
            f"current={self.current_risk_id} previous={self.previous_risk_id}>"
        )
