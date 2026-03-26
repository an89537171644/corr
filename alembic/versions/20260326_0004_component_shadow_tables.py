"""Add normalized shadow tables for element components."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260326_0004"
down_revision = "20260325_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    ensure_snapshot_table(
        table_names=table_names,
        table_name="element_section_snapshots",
        index_name="ix_element_section_snapshots_element_id",
    )
    ensure_snapshot_table(
        table_names=table_names,
        table_name="element_material_snapshots",
        index_name="ix_element_material_snapshots_element_id",
    )
    ensure_snapshot_table(
        table_names=table_names,
        table_name="element_action_snapshots",
        index_name="ix_element_action_snapshots_element_id",
    )

    backfill_snapshot_rows(
        source_column="section_data",
        target_table="element_section_snapshots",
        default_schema_version="section.v2",
    )
    backfill_snapshot_rows(
        source_column="material_data",
        target_table="element_material_snapshots",
        default_schema_version="material.v2",
    )
    backfill_snapshot_rows(
        source_column="action_data",
        target_table="element_action_snapshots",
        default_schema_version="action.v2",
    )


def ensure_snapshot_table(table_names: set[str], table_name: str, index_name: str) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table_name not in table_names:
        op.create_table(
            table_name,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("element_id", sa.Integer(), nullable=False),
            sa.Column("schema_version", sa.String(length=64), nullable=False),
            sa.Column("payload", sa.JSON(), nullable=False),
            sa.Column("source", sa.String(length=64), nullable=False, server_default="json_shadow"),
            sa.Column("synced_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["element_id"], ["elements.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("element_id"),
        )
    index_names = {index["name"] for index in inspector.get_indexes(table_name)}
    if index_name not in index_names:
        op.create_index(index_name, table_name, ["element_id"], unique=True)


def backfill_snapshot_rows(source_column: str, target_table: str, default_schema_version: str) -> None:
    bind = op.get_bind()
    metadata = sa.MetaData()
    elements = sa.Table(
        "elements",
        metadata,
        sa.Column("id", sa.Integer()),
        sa.Column(source_column, sa.JSON()),
    )
    target = sa.Table(
        target_table,
        metadata,
        sa.Column("element_id", sa.Integer()),
        sa.Column("schema_version", sa.String(length=64)),
        sa.Column("payload", sa.JSON()),
        sa.Column("source", sa.String(length=64)),
    )

    existing_ids = {
        row[0]
        for row in bind.execute(sa.select(target.c.element_id))
    }

    rows = bind.execute(sa.select(elements.c.id, getattr(elements.c, source_column))).all()
    for element_id, payload in rows:
        if element_id in existing_ids or payload is None:
            continue
        schema_version = payload.get("schema_version") or default_schema_version
        bind.execute(
            sa.insert(target).values(
                element_id=element_id,
                schema_version=schema_version,
                payload=payload,
                source="json_shadow",
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    for table_name, index_name in (
        ("element_action_snapshots", "ix_element_action_snapshots_element_id"),
        ("element_material_snapshots", "ix_element_material_snapshots_element_id"),
        ("element_section_snapshots", "ix_element_section_snapshots_element_id"),
    ):
        if table_name not in table_names:
            continue
        index_names = {index["name"] for index in inspector.get_indexes(table_name)}
        if index_name in index_names:
            op.drop_index(index_name, table_name=table_name)
        op.drop_table(table_name)
