"""Phase 4 — risk_factors + risk_evolution + extended report status

Revision ID: 0009_phase4
Revises: 0008_phase3c
Create Date: 2026-06-11

Adds `risk_factors` (extracted risks with traceability) and `risk_evolution`
(period-over-period risk changes) tables, and extends `reports.status` with
RISK_EXTRACTING / RISK_EXTRACTED. Reversible.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0009_phase4"
down_revision: str | None = "0008_phase3c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_PREV_STATUSES = (
    "UPLOADED", "PROCESSING", "PROCESSED", "SECTIONING", "SECTIONED",
    "CHUNKING", "CHUNKED", "EMBEDDING", "EMBEDDED", "EXTRACTING", "EXTRACTED",
    "COMPARING", "COMPARED", "ANALYZING", "ANALYZED", "FAILED",
)
_NEW_STATUSES = (
    "UPLOADED", "PROCESSING", "PROCESSED", "SECTIONING", "SECTIONED",
    "CHUNKING", "CHUNKED", "EMBEDDING", "EMBEDDED", "EXTRACTING", "EXTRACTED",
    "COMPARING", "COMPARED", "ANALYZING", "ANALYZED",
    "RISK_EXTRACTING", "RISK_EXTRACTED", "FAILED",
)

_RISK_CATEGORIES = (
    "SUPPLY_CHAIN", "REGULATORY", "MARKET", "COMPETITION", "TECHNOLOGY",
    "CYBERSECURITY", "OPERATIONAL", "LIQUIDITY", "GEOPOLITICAL", "LEGAL",
    "ENVIRONMENTAL", "REPUTATION", "MACROECONOMIC", "OTHER",
)

_RISK_SEVERITIES = ("LOW", "MEDIUM", "HIGH", "CRITICAL")

_EVOLUTION_TYPES = (
    "NEW_RISK", "REMOVED_RISK", "UNCHANGED_RISK", "ESCALATED_RISK", "REDUCED_RISK",
)


def _in_list(values: tuple[str, ...]) -> str:
    return "(" + ", ".join(f"'{v}'" for v in values) + ")"


def _status_check(values: tuple[str, ...]) -> str:
    return "status IN " + _in_list(values)


def upgrade() -> None:
    # ---- risk_factors --------------------------------------------------------
    op.create_table(
        "risk_factors",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"), nullable=False,
        ),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_chunk_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("risk_name", sa.Text(), nullable=False),
        sa.Column("normalized_risk_name", sa.String(length=128), nullable=False),
        sa.Column("risk_description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=20), nullable=False),
        sa.Column("severity", sa.String(length=10), nullable=False),
        sa.Column("confidence_score", sa.Numeric(4, 3), nullable=False),
        sa.Column("extraction_method", sa.String(length=20), nullable=False),
        sa.Column("source_text", sa.Text(), nullable=False),
        sa.Column("extraction_metadata", postgresql.JSONB(), nullable=False,
                  server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_risk_factors"),
        sa.ForeignKeyConstraint(
            ["company_id"], ["companies.id"],
            name="fk_risk_factors_company", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["report_id"], ["reports.id"],
            name="fk_risk_factors_report", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_chunk_id"], ["document_chunks.id"],
            name="fk_risk_factors_chunk", ondelete="SET NULL",
        ),
        sa.CheckConstraint(
            "confidence_score BETWEEN 0 AND 1",
            name="ck_risk_factors_confidence",
        ),
        sa.CheckConstraint(
            f"category IN {_in_list(_RISK_CATEGORIES)}",
            name="ck_risk_factors_category",
        ),
        sa.CheckConstraint(
            f"severity IN {_in_list(_RISK_SEVERITIES)}",
            name="ck_risk_factors_severity",
        ),
        sa.CheckConstraint(
            "extraction_method IN ('RULE_BASED','LLM_BASED','HYBRID_VALIDATED')",
            name="ck_risk_factors_method",
        ),
    )
    op.create_index("ix_risk_factors_company_id", "risk_factors", ["company_id"])
    op.create_index("ix_risk_factors_report_id", "risk_factors", ["report_id"])
    op.create_index("ix_risk_factors_source_chunk_id", "risk_factors", ["source_chunk_id"])
    op.create_index("ix_risk_factors_category", "risk_factors", ["category"])
    op.create_index("ix_risk_factors_severity", "risk_factors", ["severity"])
    op.create_index(
        "ix_risk_factors_company_category", "risk_factors", ["company_id", "category"]
    )

    # ---- risk_evolution ------------------------------------------------------
    op.create_table(
        "risk_evolution",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"), nullable=False,
        ),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("current_risk_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("previous_risk_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("evolution_type", sa.String(length=20), nullable=False),
        sa.Column("confidence_score", sa.Numeric(4, 3), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_risk_evolution"),
        sa.ForeignKeyConstraint(
            ["company_id"], ["companies.id"],
            name="fk_risk_evolution_company", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["current_risk_id"], ["risk_factors.id"],
            name="fk_risk_evolution_current", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["previous_risk_id"], ["risk_factors.id"],
            name="fk_risk_evolution_previous", ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "confidence_score BETWEEN 0 AND 1",
            name="ck_risk_evolution_confidence",
        ),
        sa.CheckConstraint(
            f"evolution_type IN {_in_list(_EVOLUTION_TYPES)}",
            name="ck_risk_evolution_type",
        ),
    )
    op.create_index("ix_risk_evolution_company_id", "risk_evolution", ["company_id"])
    op.create_index("ix_risk_evolution_current_risk_id", "risk_evolution", ["current_risk_id"])
    op.create_index("ix_risk_evolution_previous_risk_id", "risk_evolution", ["previous_risk_id"])

    # ---- extend report status ------------------------------------------------
    op.execute("ALTER TABLE reports DROP CONSTRAINT IF EXISTS ck_reports_report_status")
    op.create_check_constraint("report_status", "reports", _status_check(_NEW_STATUSES))


def downgrade() -> None:
    # revert report status
    op.execute(
        "UPDATE reports SET status = 'FAILED' "
        "WHERE status IN ('RISK_EXTRACTING', 'RISK_EXTRACTED')"
    )
    op.execute("ALTER TABLE reports DROP CONSTRAINT IF EXISTS ck_reports_report_status")
    op.create_check_constraint("report_status", "reports", _status_check(_PREV_STATUSES))

    # drop evolution
    op.drop_index("ix_risk_evolution_previous_risk_id", table_name="risk_evolution")
    op.drop_index("ix_risk_evolution_current_risk_id", table_name="risk_evolution")
    op.drop_index("ix_risk_evolution_company_id", table_name="risk_evolution")
    op.drop_table("risk_evolution")

    # drop risk_factors
    op.drop_index("ix_risk_factors_company_category", table_name="risk_factors")
    op.drop_index("ix_risk_factors_severity", table_name="risk_factors")
    op.drop_index("ix_risk_factors_category", table_name="risk_factors")
    op.drop_index("ix_risk_factors_source_chunk_id", table_name="risk_factors")
    op.drop_index("ix_risk_factors_report_id", table_name="risk_factors")
    op.drop_index("ix_risk_factors_company_id", table_name="risk_factors")
    op.drop_table("risk_factors")
