"""FastAPI application entrypoint.

Exposes a factory to construct the app and a module-level ``app`` instance.
Behavior is unchanged; formatting/docstrings/typing follow the golden style.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.routers import admin_config, admin_chaos, meta, schemas

__all__ = ["create_app", "app"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Warm configuration and generator caches on startup."""
    from server.deps import get_settings, warmup_all

    warmup_all()
    get_settings()
    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        FastAPI: Configured application instance.
    """
    app = FastAPI(title="Mock Data API", version="0.1.0", lifespan=lifespan)

    # TODO(config): Make CORS policy configurable via settings.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(admin_chaos.router)
    app.include_router(meta.router)
    app.include_router(schemas.router)
    app.include_router(admin_config.router)

    return app


app = create_app()
