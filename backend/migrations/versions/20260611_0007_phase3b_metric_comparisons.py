"""Phase 3B — metric_comparisons + extended report status

Revision ID: 0007_phase3b
Revises: 0006_phase3a
Create Date: 2026-06-11

Adds the `metric_comparisons` table (deterministic period-over-period deltas —
ADR-007/ADR-018) and extends `reports.status` with COMPARING / COMPARED.
Reversible.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0007_phase3b"
down_revision: str | None = "0006_phase3a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_PREV_STATUSES = (
    "UPLOADED", "PROCESSING", "PROCESSED", "SECTIONING", "SECTIONED",
    "CHUNKING", "CHUNKED", "EMBEDDING", "EMBEDDED", "EXTRACTING", "EXTRACTED", "FAILED",
)
_NEW_STATUSES = (
    "UPLOADED", "PROCESSING", "PROCESSED", "SECTIONING", "SECTIONED",
    "CHUNKING", "CHUNKED", "EMBEDDING", "EMBEDDED", "EXTRACTING", "EXTRACTED",
    "COMPARING", "COMPARED", "FAILED",
)


def _status_check(values: tuple[str, ...]) -> str:
    return "status IN (" + ", ".join(f"'{v}'" for v in values) + ")"


def upgrade() -> None:
    op.create_table(
        "metric_comparisons",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"), nullable=False,
        ),
        sa.Column("metric_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("metric_name", sa.String(length=64), nullable=False),
        sa.Column("comparison_type", sa.String(length=8), nullable=False),
        sa.Column("current_period", sa.String(length=16), nullable=False),
        sa.Column("previous_period", sa.String(length=16), nullable=False),
        sa.Column("current_value", sa.Numeric(), nullable=False),
        sa.Column("previous_value", sa.Numeric(), nullable=False),
        sa.Column("absolute_change", sa.Numeric(), nullable=True),
        sa.Column("percentage_change", sa.Numeric(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_metric_comparisons"),
        sa.ForeignKeyConstraint(
            ["metric_id"], ["financial_metrics.id"],
            name="fk_metric_comparisons_metric_id_financial_metrics", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"], ["companies.id"],
            name="fk_metric_comparisons_company_id_companies", ondelete="CASCADE",
        ),
        sa.UniqueConstraint("metric_id", "comparison_type", name="uq_metric_comparisons_metric_type"),
        sa.CheckConstraint(
            "comparison_type IN ('YOY','QOQ','YTD','TTM')", name="ck_metric_comparisons_type"
        ),
    )
    op.create_index("ix_metric_comparisons_company_id", "metric_comparisons", ["company_id"])
    op.create_index("ix_metric_comparisons_metric_id", "metric_comparisons", ["metric_id"])
    op.create_index(
        "ix_metric_comparisons_company_metric", "metric_comparisons", ["company_id", "metric_name"]
    )
    op.create_index("ix_metric_comparisons_type", "metric_comparisons", ["comparison_type"])

    op.execute("ALTER TABLE reports DROP CONSTRAINT IF EXISTS ck_reports_report_status")
    op.create_check_constraint("report_status", "reports", _status_check(_NEW_STATUSES))


def downgrade() -> None:
    op.execute(
        "UPDATE reports SET status = 'FAILED' WHERE status IN ('COMPARING', 'COMPARED')"
    )
    op.execute("ALTER TABLE reports DROP CONSTRAINT IF EXISTS ck_reports_report_status")
    op.create_check_constraint("report_status", "reports", _status_check(_PREV_STATUSES))

    op.drop_index("ix_metric_comparisons_type", table_name="metric_comparisons")
    op.drop_index("ix_metric_comparisons_company_metric", table_name="metric_comparisons")
    op.drop_index("ix_metric_comparisons_metric_id", table_name="metric_comparisons")
    op.drop_index("ix_metric_comparisons_company_id", table_name="metric_comparisons")
    op.drop_table("metric_comparisons")
