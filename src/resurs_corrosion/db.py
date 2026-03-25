from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Generator, Optional

from fastapi import Request
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from .models import Base

DEFAULT_DATABASE_URL = "sqlite:///./app.db"
DEFAULT_SCHEMA_MODE = "auto"
VALID_SCHEMA_MODES = {"auto", "create_all", "migrate", "skip"}
DEFAULT_MIGRATION_ATTEMPTS = 10
DEFAULT_MIGRATION_DELAY_SECONDS = 2.0


def normalize_database_url(database_url: Optional[str] = None) -> str:
    raw_url = database_url or os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
    if raw_url.startswith("postgres://"):
        return raw_url.replace("postgres://", "postgresql+psycopg://", 1)
    if raw_url.startswith("postgresql://"):
        return raw_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return raw_url


def build_engine(database_url: Optional[str] = None) -> Engine:
    url = normalize_database_url(database_url)
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, future=True, pool_pre_ping=True, connect_args=connect_args)


def build_session_factory(engine: Engine) -> sessionmaker:
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_session(request: Request) -> Generator:
    session_factory = request.app.state.session_factory
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def resolve_schema_mode(database_url: str, schema_mode: Optional[str] = None) -> str:
    mode = (schema_mode or os.getenv("DB_SCHEMA_MODE", DEFAULT_SCHEMA_MODE)).strip().lower()
    if mode not in VALID_SCHEMA_MODES:
        raise ValueError(
            f"Unsupported DB_SCHEMA_MODE '{mode}'. Expected one of: {', '.join(sorted(VALID_SCHEMA_MODES))}."
        )

    if mode != "auto":
        return mode

    return "create_all" if database_url.startswith("sqlite") else "skip"


def initialize_database_schema(
    engine: Engine,
    database_url: str,
    schema_mode: Optional[str] = None,
) -> str:
    resolved_mode = resolve_schema_mode(database_url, schema_mode)

    if resolved_mode == "create_all":
        Base.metadata.create_all(bind=engine)
    elif resolved_mode == "migrate":
        run_alembic_upgrade(database_url)

    return resolved_mode


def run_alembic_upgrade(database_url: str) -> None:
    from alembic import command
    from alembic.config import Config

    project_root = Path(__file__).resolve().parents[2]
    attempts = int(os.getenv("DB_MIGRATION_MAX_ATTEMPTS", str(DEFAULT_MIGRATION_ATTEMPTS)))
    delay_seconds = float(os.getenv("DB_MIGRATION_RETRY_DELAY_SECONDS", str(DEFAULT_MIGRATION_DELAY_SECONDS)))
    last_error: Optional[Exception] = None

    for attempt in range(1, attempts + 1):
        try:
            config = Config(str(project_root / "alembic.ini"))
            config.set_main_option("script_location", str(project_root / "alembic"))
            config.set_main_option("sqlalchemy.url", database_url)
            command.upgrade(config, "head")
            return
        except Exception as exc:
            last_error = exc
            if attempt == attempts:
                break
            time.sleep(delay_seconds)

    if last_error is not None:
        raise last_error
