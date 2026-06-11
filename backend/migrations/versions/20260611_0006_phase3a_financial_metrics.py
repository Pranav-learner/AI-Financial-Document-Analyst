"""Phase 3A — financial_metrics + extended report status

Revision ID: 0006_phase3a
Revises: 0005_phase2b
Create Date: 2026-06-11

Adds the `financial_metrics` table (structured, validated, traceable extracted
metrics — ADR-007/ADR-017) and extends `reports.status` with EXTRACTING /
EXTRACTED. Reversible.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0006_phase3a"
down_revision: str | None = "0005_phase2b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_PREV_STATUSES = (
    "UPLOADED", "PROCESSING", "PROCESSED", "SECTIONING", "SECTIONED",
    "CHUNKING", "CHUNKED", "EMBEDDING", "EMBEDDED", "FAILED",
)
_NEW_STATUSES = (
    "UPLOADED", "PROCESSING", "PROCESSED", "SECTIONING", "SECTIONED",
    "CHUNKING", "CHUNKED", "EMBEDDING", "EMBEDDED", "EXTRACTING", "EXTRACTED", "FAILED",
)


def _status_check(values: tuple[str, ...]) -> str:
    return "status IN (" + ", ".join(f"'{v}'" for v in values) + ")"


def upgrade() -> None:
    op.create_table(
        "financial_metrics",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"), nullable=False,
        ),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_chunk_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("metric_name", sa.Text(), nullable=False),
        sa.Column("normalized_metric_name", sa.String(length=64), nullable=False),
        sa.Column("metric_category", sa.String(length=16), nullable=False),
        sa.Column("value", sa.Numeric(), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=True),
        sa.Column("unit", sa.String(length=16), nullable=False),
        sa.Column("fiscal_year", sa.Integer(), nullable=True),
        sa.Column("fiscal_quarter", sa.Integer(), nullable=True),
        sa.Column("confidence_score", sa.Numeric(4, 3), nullable=False),
        sa.Column("extraction_method", sa.String(length=20), nullable=False),
        sa.Column("source_text", sa.Text(), nullable=False),
        sa.Column(
            "extraction_metadata", postgresql.JSONB(), nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_financial_metrics"),
        sa.ForeignKeyConstraint(
            ["report_id"], ["reports.id"],
            name="fk_financial_metrics_report_id_reports", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_chunk_id"], ["document_chunks.id"],
            name="fk_financial_metrics_source_chunk_id_document_chunks", ondelete="SET NULL",
        ),
        sa.CheckConstraint("confidence_score BETWEEN 0 AND 1", name="ck_financial_metrics_confidence"),
        sa.CheckConstraint(
            "fiscal_quarter IS NULL OR (fiscal_quarter BETWEEN 1 AND 4)",
            name="ck_financial_metrics_quarter",
        ),
        sa.CheckConstraint(
            "metric_category IN ('REVENUE','PROFITABILITY','MARGINS','CASH_FLOW',"
            "'DEBT','CAPEX','GUIDANCE','OTHER')",
            name="ck_financial_metrics_category",
        ),
        sa.CheckConstraint(
            "extraction_method IN ('RULE_BASED','LLM_BASED','HYBRID_VALIDATED')",
            name="ck_financial_metrics_method",
        ),
    )
    op.create_index("ix_financial_metrics_report_id", "financial_metrics", ["report_id"])
    op.create_index(
        "ix_financial_metrics_source_chunk_id", "financial_metrics", ["source_chunk_id"]
    )
    op.create_index(
        "ix_financial_metrics_normalized_name",
        "financial_metrics", ["report_id", "normalized_metric_name"],
    )
    op.create_index("ix_financial_metrics_category", "financial_metrics", ["metric_category"])

    # ---- extend reports.status allowed values (bare name → naming convention) -
    op.execute("ALTER TABLE reports DROP CONSTRAINT IF EXISTS ck_reports_report_status")
    op.create_check_constraint("report_status", "reports", _status_check(_NEW_STATUSES))


def downgrade() -> None:
    op.execute(
        "UPDATE reports SET status = 'FAILED' WHERE status IN ('EXTRACTING', 'EXTRACTED')"
    )
    op.execute("ALTER TABLE reports DROP CONSTRAINT IF EXISTS ck_reports_report_status")
    op.create_check_constraint("report_status", "reports", _status_check(_PREV_STATUSES))

    op.drop_index("ix_financial_metrics_category", table_name="financial_metrics")
    op.drop_index("ix_financial_metrics_normalized_name", table_name="financial_metrics")
    op.drop_index("ix_financial_metrics_source_chunk_id", table_name="financial_metrics")
    op.drop_index("ix_financial_metrics_report_id", table_name="financial_metrics")
    op.drop_table("financial_metrics")
