from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .api import router
from .db import build_engine, build_session_factory, initialize_database_schema, normalize_database_url
from .services.bootstrap import seed_demo_workspace_if_empty
from .services.reports import DEFAULT_REPORTS_DIR


def create_app(database_url: Optional[str] = None, seed_demo_data: Optional[bool] = None) -> FastAPI:
    resolved_database_url = normalize_database_url(database_url)
    engine = build_engine(resolved_database_url)
    session_factory = build_session_factory(engine)
    reports_dir = DEFAULT_REPORTS_DIR.resolve()
    reports_dir.mkdir(parents=True, exist_ok=True)
    web_dir = (Path(__file__).resolve().parent / "web").resolve()
    should_seed_demo = resolve_demo_seed_flag(seed_demo_data)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        schema_mode = initialize_database_schema(engine, resolved_database_url)
        app.state.engine = engine
        app.state.session_factory = session_factory
        app.state.database_url = resolved_database_url
        app.state.reports_dir = reports_dir
        app.state.db_schema_mode = schema_mode
        app.state.demo_seed_enabled = should_seed_demo
        app.state.demo_seed_applied = seed_demo_workspace_if_empty(session_factory) if should_seed_demo else False
        try:
            yield
        finally:
            engine.dispose()

    app = FastAPI(
        title="Система оценки коррозии и остаточного ресурса",
        version="0.8.0",
        description="API для оценки атмосферной коррозии, остаточной несущей способности и прогноза остаточного ресурса.",
        lifespan=lifespan,
    )
    app.include_router(router)
    app.mount("/static", StaticFiles(directory=web_dir), name="static")

    @app.get("/", include_in_schema=False)
    def root() -> FileResponse:
        return FileResponse(web_dir / "index.html")

    return app


def resolve_demo_seed_flag(seed_demo_data: Optional[bool] = None) -> bool:
    if seed_demo_data is not None:
        return seed_demo_data

    raw_value = os.getenv("APP_SEED_DEMO_DATA", "1").strip().lower()
    return raw_value not in {"0", "false", "no", "off"}


app = create_app()
