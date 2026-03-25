"""Add measurement units and comment fields."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260325_0002"
down_revision = "20260325_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("measurements", sa.Column("units", sa.String(length=32), nullable=False, server_default="mm"))
    op.add_column("measurements", sa.Column("comment", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("measurements", "comment")
    op.drop_column("measurements", "units")
