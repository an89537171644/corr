from __future__ import annotations

from pathlib import Path

from sqlalchemy import inspect
from sqlalchemy.orm import sessionmaker

from resurs_corrosion.db import build_engine, initialize_database_schema, resolve_schema_mode, run_alembic_upgrade
from resurs_corrosion.domain import ActionInput, AssetCreate, ElementCreate, EnvironmentCategory, MaterialInput, SectionDefinition, ZoneDefinition
from resurs_corrosion.models import Base
from resurs_corrosion.storage import create_asset, create_element


def test_resolve_schema_mode_auto_for_sqlite() -> None:
    assert resolve_schema_mode("sqlite:///./app.db", "auto") == "create_all"


def test_resolve_schema_mode_auto_for_postgres() -> None:
    assert resolve_schema_mode("postgresql+psycopg://user:pass@localhost/db", "auto") == "skip"


def test_initialize_database_schema_create_all_creates_tables(tmp_path: Path) -> None:
    database_path = tmp_path / "schema.db"
    database_url = f"sqlite:///{database_path}"
    engine = build_engine(database_url)

    mode = initialize_database_schema(engine, database_url, "create_all")

    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())

    assert mode == "create_all"
    assert {
        "assets",
        "elements",
        "zones",
        "inspections",
        "measurements",
        "analysis_runs",
        "element_section_snapshots",
        "element_material_snapshots",
        "element_action_snapshots",
    } <= table_names
    measurement_columns = {column["name"] for column in inspector.get_columns("measurements")}
    assert {"units", "comment"} <= measurement_columns
    analysis_columns = {column["name"] for column in inspector.get_columns("analysis_runs")}
    assert {"element_id", "request_data", "result_data"} <= analysis_columns
    snapshot_columns = {column["name"] for column in inspector.get_columns("element_section_snapshots")}
    assert {"element_id", "schema_version", "payload", "source"} <= snapshot_columns

    engine.dispose()


def test_run_alembic_upgrade_handles_precreated_analysis_runs(tmp_path: Path) -> None:
    database_path = tmp_path / "legacy.db"
    database_url = f"sqlite:///{database_path}"
    engine = build_engine(database_url)
    Base.metadata.create_all(bind=engine)

    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) NOT NULL)")
        connection.exec_driver_sql("DELETE FROM alembic_version")
        connection.exec_driver_sql("INSERT INTO alembic_version (version_num) VALUES ('20260325_0002')")

    run_alembic_upgrade(database_url)

    with engine.connect() as connection:
        version = connection.exec_driver_sql("SELECT version_num FROM alembic_version").scalar_one()

    assert version == "20260326_0004"

    engine.dispose()


def test_element_write_populates_shadow_component_tables(tmp_path: Path) -> None:
    database_path = tmp_path / "shadow.db"
    engine = build_engine(f"sqlite:///{database_path}")
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)()

    asset = create_asset(session, AssetCreate(name="Shadow asset"))
    create_element(
        session,
        asset.id,
        ElementCreate(
            element_id="EL-1",
            element_type="column",
            environment_category=EnvironmentCategory.C3,
            current_service_life_years=12.0,
            section=SectionDefinition(section_type="plate", width_mm=200.0, thickness_mm=12.0),
            zones=[ZoneDefinition(zone_id="z1", role="plate", initial_thickness_mm=12.0)],
            material=MaterialInput(fy_mpa=245.0, gamma_m=1.05, stability_factor=0.9),
            action=ActionInput(check_type="axial_tension", demand_value=180.0),
        ),
    )

    with engine.connect() as connection:
        section_count = connection.exec_driver_sql("SELECT COUNT(*) FROM element_section_snapshots").scalar_one()
        material_count = connection.exec_driver_sql("SELECT COUNT(*) FROM element_material_snapshots").scalar_one()
        action_count = connection.exec_driver_sql("SELECT COUNT(*) FROM element_action_snapshots").scalar_one()

    assert section_count == 1
    assert material_count == 1
    assert action_count == 1

    engine.dispose()
