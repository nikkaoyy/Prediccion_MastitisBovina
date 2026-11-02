"""Aplicación FastAPI del servidor de sincronización y modelo."""

from __future__ import annotations

import json

from fastapi import FastAPI

from server.app import monitoring
from server.app.config import Settings
from server.app.db import Base, make_engine, make_session_factory
from server.app.routers import model, sync


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    app = FastAPI(
        title="Mastitis — servidor de sincronización",
        version="0.1.0",
        description=(
            "Apoyo a la decisión: las estimaciones de riesgo no constituyen "
            "diagnóstico ni sustituyen la valoración veterinaria."
        ),
    )

    lite = json.loads((settings.models_dir / "model_lite.json").read_text(encoding="utf-8"))
    engine = make_engine(settings.database_url)
    Base.metadata.create_all(engine)

    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = make_session_factory(engine)
    app.state.ranges = lite["ranges"]
    app.state.model_version = lite["model_version"]

    app.include_router(sync.router)
    app.include_router(model.router)
    app.include_router(monitoring.router)

    @app.get("/health", tags=["health"])
    def health() -> dict:
        return {"status": "ok", "model_version": app.state.model_version}

    return app


def _default_app() -> FastAPI:
    return create_app()


# `uvicorn server.app.main:app` (carga diferida para no exigir el modelo al importar)
def __getattr__(name: str):
    if name == "app":
        return _default_app()
    raise AttributeError(name)
