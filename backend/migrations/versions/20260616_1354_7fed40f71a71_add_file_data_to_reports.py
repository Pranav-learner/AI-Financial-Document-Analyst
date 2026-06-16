"""add_file_data_to_reports

Revision ID: 7fed40f71a71
Revises: 98d7c4311fb1
Create Date: 2026-06-16 13:54:35.170119+00:00
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7fed40f71a71'
down_revision: str | None = '98d7c4311fb1'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('reports', sa.Column('file_data', sa.LargeBinary(), nullable=True))


def downgrade() -> None:
    op.drop_column('reports', 'file_data')
