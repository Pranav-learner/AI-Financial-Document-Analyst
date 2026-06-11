"""Phase 3C — financial_analytics + extended report status

Revision ID: 0008_phase3c
Revises: 0007_phase3b
Create Date: 2026-06-11

Adds the `financial_analytics` table (deterministic signals/ratios/classifications)
and extends `reports.status` with ANALYZING / ANALYZED.
Reversible.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0008_phase3c"
down_revision: str | None = "0007_phase3b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_PREV_STATUSES = (
    "UPLOADED", "PROCESSING", "PROCESSED", "SECTIONING", "SECTIONED",
    "CHUNKING", "CHUNKED", "EMBEDDING", "EMBEDDED", "EXTRACTING", "EXTRACTED",
    "COMPARING", "COMPARED", "FAILED",
)
_NEW_STATUSES = (
    "UPLOADED", "PROCESSING", "PROCESSED", "SECTIONING", "SECTIONED",
    "CHUNKING", "CHUNKED", "EMBEDDING", "EMBEDDED", "EXTRACTING", "EXTRACTED",
    "COMPARING", "COMPARED", "ANALYZING", "ANALYZED", "FAILED",
)


def _status_check(values: tuple[str, ...]) -> str:
    return "status IN (" + ", ".join(f"'{v}'" for v in values) + ")"


def upgrade() -> None:
    op.create_table(
        "financial_analytics",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"), nullable=False,
        ),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("metric_name", sa.String(length=64), nullable=True),
        sa.Column("signal_type", sa.String(length=20), nullable=False),
        sa.Column("signal_code", sa.String(length=64), nullable=False),
        sa.Column("value", sa.Numeric(), nullable=True),
        sa.Column("classification", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("supporting_metric_ids", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_financial_analytics"),
        sa.ForeignKeyConstraint(
            ["company_id"], ["companies.id"],
            name="fk_financial_analytics_company_id_companies", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["report_id"], ["reports.id"],
            name="fk_financial_analytics_report_id_reports", ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "signal_type IN ('GROWTH', 'PROFITABILITY', 'LIQUIDITY', 'LEVERAGE', 'CASH_FLOW', 'EFFICIENCY', 'GUIDANCE', 'GENERAL')",
            name="ck_financial_analytics_type"
        ),
        sa.CheckConstraint(
            "severity IN ('VERY_POSITIVE', 'POSITIVE', 'NEUTRAL', 'NEGATIVE', 'VERY_NEGATIVE')",
            name="ck_financial_analytics_severity"
        ),
    )
    op.create_index("ix_financial_analytics_company_id", "financial_analytics", ["company_id"])
    op.create_index("ix_financial_analytics_report_id", "financial_analytics", ["report_id"])
    op.create_index(
        "ix_financial_analytics_company_type", "financial_analytics", ["company_id", "signal_type"]
    )

    op.execute("ALTER TABLE reports DROP CONSTRAINT IF EXISTS ck_reports_report_status")
    op.create_check_constraint("report_status", "reports", _status_check(_NEW_STATUSES))


def downgrade() -> None:
    op.execute(
        "UPDATE reports SET status = 'FAILED' WHERE status IN ('ANALYZING', 'ANALYZED')"
    )
    op.execute("ALTER TABLE reports DROP CONSTRAINT IF EXISTS ck_reports_report_status")
    op.create_check_constraint("report_status", "reports", _status_check(_PREV_STATUSES))

    op.drop_index("ix_financial_analytics_company_type", table_name="financial_analytics")
    op.drop_index("ix_financial_analytics_report_id", table_name="financial_analytics")
    op.drop_index("ix_financial_analytics_company_id", table_name="financial_analytics")
    op.drop_table("financial_analytics")
