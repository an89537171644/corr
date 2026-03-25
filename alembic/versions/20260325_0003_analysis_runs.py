"""Add persisted analysis runs."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260325_0003"
down_revision = "20260325_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "analysis_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("element_id", sa.Integer(), nullable=True),
        sa.Column("request_data", sa.JSON(), nullable=False),
        sa.Column("result_data", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["element_id"], ["elements.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_analysis_runs_element_id", "analysis_runs", ["element_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_analysis_runs_element_id", table_name="analysis_runs")
    op.drop_table("analysis_runs")
