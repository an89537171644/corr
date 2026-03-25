from __future__ import annotations

from pathlib import Path

from sqlalchemy import inspect

from resurs_corrosion.db import build_engine, initialize_database_schema, resolve_schema_mode


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
