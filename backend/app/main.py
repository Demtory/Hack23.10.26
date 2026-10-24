# Aéza - это быстрый хостинг
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from .api import _ensure_summary, _metrics_text, _validate_settings, router
from .config import ROOT, Config
from .db import connect, init_db, transaction
from .security import ensure_admin
from .seed import ensure_seed, ensure_source_meta, get_settings
from .store import recompute


def create_app(config: Config | None = None) -> FastAPI:
    cfg = config or Config.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        conn = connect(cfg.db_path)
        try:
            init_db(conn)
            ensure_admin(conn, cfg.admin_email, cfg.admin_password)
            with transaction(conn):
                get_settings(conn)
                ensure_source_meta(conn)
                ensure_seed(conn, cfg.seed_path, cfg.seed_on_start)
                settings, version, _ = get_settings(conn)
                _validate_settings(settings)
                recompute(conn, settings, version, cfg.as_of)
        finally:
            conn.close()
        yield

    app = FastAPI(
        title="Churn Risk Analyzer",
        description="Анализатор рисков оттока: кому звонить, почему и сколько денег под угрозой.",
        version="0.1.0",
        docs_url="/api/v1/docs",
        redoc_url=None,
        openapi_url="/api/v1/openapi.json",
        lifespan=lifespan,
    )
    @app.exception_handler(RequestValidationError)
    async def validation_error(_request: Request, exc: RequestValidationError):
        # Input/ctx can contain NaN, arbitrary objects or sensitive snapshot fields.
        errors = [{key: error[key] for key in ("loc", "msg", "type") if key in error}
                  for error in exc.errors()]
        return JSONResponse(status_code=422, content={"detail": errors})

    app.state.config = cfg
    app.include_router(router)

    @app.get("/healthz", tags=["system"])
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/metrics", tags=["system"], summary="Prometheus metrics")
    def metrics_root(request: Request) -> PlainTextResponse:
        conn = connect(request.app.state.config.db_path)
        try:
            summary = _ensure_summary(conn, request.app.state.config)
        finally:
            conn.close()
        return PlainTextResponse(
            _metrics_text(summary),
            media_type="text/plain; version=0.0.4; charset=utf-8",
        )

    static_dir = ROOT / "frontend" / "dist"
    if static_dir.exists():
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="frontend")
    else:
        @app.get("/", include_in_schema=False)
        def root() -> dict[str, str]:
            return {
                "name": "Churn Risk Analyzer API",
                "docs": "/api/v1/docs",
                "health": "/healthz",
                "metrics": "/metrics",
            }

    return app


app = create_app()
