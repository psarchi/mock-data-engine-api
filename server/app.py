from __future__ import annotations
from datetime import datetime, UTC
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from server.routers import meta, validate, generate, schemas, admin_config


def create_app() -> FastAPI:
    app = FastAPI(title="Mock Data API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,  # type: ignore[arg-type]
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(meta.router)
    app.include_router(validate.router)
    app.include_router(generate.router)
    app.include_router(schemas.router)
    app.include_router(admin_config.router)
    return app


app = create_app()
