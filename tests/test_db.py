from __future__ import annotations

from pathlib import Path

from sqlalchemy import inspect

from resurs_corrosion.db import build_engine, initialize_database_schema, resolve_schema_mode, run_alembic_upgrade
from resurs_corrosion.models import Base


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
    assert {"assets", "elements", "zones", "inspections", "measurements", "analysis_runs"} <= table_names
    measurement_columns = {column["name"] for column in inspector.get_columns("measurements")}
    assert {"units", "comment"} <= measurement_columns
    analysis_columns = {column["name"] for column in inspector.get_columns("analysis_runs")}
    assert {"element_id", "request_data", "result_data"} <= analysis_columns

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

    assert version == "20260325_0003"

    engine.dispose()
