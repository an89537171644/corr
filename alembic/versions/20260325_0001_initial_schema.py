"""Initial schema for the corrosion MVP."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260325_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "assets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("address", sa.String(length=500), nullable=True),
        sa.Column("commissioned_year", sa.Integer(), nullable=True),
        sa.Column("purpose", sa.String(length=255), nullable=True),
        sa.Column("responsibility_class", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "elements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("element_code", sa.String(length=100), nullable=False),
        sa.Column("element_type", sa.String(length=100), nullable=False),
        sa.Column("steel_grade", sa.String(length=100), nullable=True),
        sa.Column("work_scheme", sa.String(length=255), nullable=True),
        sa.Column("operating_zone", sa.String(length=255), nullable=True),
        sa.Column("environment_category", sa.String(length=10), nullable=False),
        sa.Column("current_service_life_years", sa.Float(), nullable=False, server_default="0"),
        sa.Column("section_data", sa.JSON(), nullable=False),
        sa.Column("material_data", sa.JSON(), nullable=False),
        sa.Column("action_data", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_elements_asset_id", "elements", ["asset_id"], unique=False)

    op.create_table(
        "zones",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("element_id", sa.Integer(), nullable=False),
        sa.Column("zone_code", sa.String(length=100), nullable=False),
        sa.Column("role", sa.String(length=100), nullable=False),
        sa.Column("initial_thickness_mm", sa.Float(), nullable=False),
        sa.Column("exposed_surfaces", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("pitting_factor", sa.Float(), nullable=False, server_default="0"),
        sa.Column("pit_loss_mm", sa.Float(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["element_id"], ["elements.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_zones_element_id", "zones", ["element_id"], unique=False)

    op.create_table(
        "inspections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("element_id", sa.Integer(), nullable=False),
        sa.Column("inspection_code", sa.String(length=100), nullable=True),
        sa.Column("performed_at", sa.Date(), nullable=False),
        sa.Column("method", sa.String(length=255), nullable=False),
        sa.Column("executor", sa.String(length=255), nullable=True),
        sa.Column("findings", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["element_id"], ["elements.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_inspections_element_id", "inspections", ["element_id"], unique=False)

    op.create_table(
        "measurements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("inspection_id", sa.Integer(), nullable=False),
        sa.Column("zone_code", sa.String(length=100), nullable=False),
        sa.Column("point_id", sa.String(length=100), nullable=True),
        sa.Column("thickness_mm", sa.Float(), nullable=False),
        sa.Column("error_mm", sa.Float(), nullable=False, server_default="0"),
        sa.Column("measured_at", sa.Date(), nullable=True),
        sa.Column("quality", sa.Float(), nullable=False, server_default="1"),
        sa.ForeignKeyConstraint(["inspection_id"], ["inspections.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_measurements_inspection_id", "measurements", ["inspection_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_measurements_inspection_id", table_name="measurements")
    op.drop_table("measurements")
    op.drop_index("ix_inspections_element_id", table_name="inspections")
    op.drop_table("inspections")
    op.drop_index("ix_zones_element_id", table_name="zones")
    op.drop_table("zones")
    op.drop_index("ix_elements_asset_id", table_name="elements")
    op.drop_table("elements")
    op.drop_table("assets")
