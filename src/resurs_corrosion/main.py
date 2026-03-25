from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .api import router
from .db import build_engine, build_session_factory, initialize_database_schema, normalize_database_url
from .services.reports import DEFAULT_REPORTS_DIR


def create_app(database_url: Optional[str] = None) -> FastAPI:
    resolved_database_url = normalize_database_url(database_url)
    engine = build_engine(resolved_database_url)
    session_factory = build_session_factory(engine)
    reports_dir = DEFAULT_REPORTS_DIR.resolve()
    reports_dir.mkdir(parents=True, exist_ok=True)
    web_dir = (Path(__file__).resolve().parent / "web").resolve()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        schema_mode = initialize_database_schema(engine, resolved_database_url)
        app.state.engine = engine
        app.state.session_factory = session_factory
        app.state.database_url = resolved_database_url
        app.state.reports_dir = reports_dir
        app.state.db_schema_mode = schema_mode
        try:
            yield
        finally:
            engine.dispose()

    app = FastAPI(
        title="Residual Life Corrosion MVP",
        version="0.6.0",
        description="Baseline API for atmospheric corrosion assessment and residual life forecasting.",
        lifespan=lifespan,
    )
    app.include_router(router)
    app.mount("/static", StaticFiles(directory=web_dir), name="static")

    @app.get("/", include_in_schema=False)
    def root() -> FileResponse:
        return FileResponse(web_dir / "index.html")

    return app


app = create_app()
