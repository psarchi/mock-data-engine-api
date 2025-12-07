"""FastAPI application entrypoint.

Exposes a factory to construct the app and a module-level ``app`` instance.
Behavior is unchanged; formatting/docstrings/typing follow the golden style.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.routers import admin_config, admin_chaos, meta, schemas, data
from server.errors import build_error_response, build_unhandled_response
from server.logging import setup_logging
from server.middleware.correlation import CorrelationMiddleware
from server.middleware.metrics import MetricsMiddleware
from mock_engine.errors import MockEngineError
from mock_engine.observability import get_metrics_app

__all__ = ["create_app", "app"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Warm configuration and generator caches on startup."""
    import asyncio
    from server.deps import get_settings, warmup_all
    from mock_engine.persistence.metrics_collector import MetricsCollector
    from mock_engine.persistence import StorageManager

    # Setup structured logging
    setup_logging()

    warmup_all()
    cm = get_settings()

    # Read persistence config
    try:
        persistence_cfg = cm.get_root("server").persistence  # type: ignore
        redis_url = getattr(persistence_cfg.redis, "url", None)
        metrics_interval = getattr(persistence_cfg.metrics_collector, "interval_seconds", 30)
    except (AttributeError, TypeError):
        redis_url = None
        metrics_interval = 30

    # Initialize shared Redis client (API only writes to Redis)
    from mock_engine.persistence import RedisClient
    redis = RedisClient(redis_url)
    await redis.connect()
    app.state.redis = redis

    # Start metrics collector in background
    metrics_collector = MetricsCollector(interval_seconds=metrics_interval)
    collector_task = asyncio.create_task(metrics_collector.start())

    yield

    # Stop metrics collector on shutdown
    await metrics_collector.stop()
    collector_task.cancel()
    try:
        await collector_task
    except asyncio.CancelledError:
        pass

    # Close Redis connection
    await redis.close()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        FastAPI: Configured application instance.
    """
    app = FastAPI(title="Mock Data API", version="0.1.0", lifespan=lifespan)

    app.add_middleware(CorrelationMiddleware)

    from mock_engine.config import get_config_manager
    try:
        server_cfg = get_config_manager().get_root("server")
        metrics_enabled = server_cfg.observability.metrics_enabled  # type: ignore
        metrics_path = server_cfg.observability.prometheus_path  # type: ignore
    except (AttributeError, TypeError):
        metrics_enabled = False
        metrics_path = "/metrics"

    if metrics_enabled:
        app.add_middleware(MetricsMiddleware)

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
    app.include_router(admin_config.router)
    app.include_router(schemas.router)
    app.include_router(data.router)

    if metrics_enabled:
        app.mount(metrics_path, get_metrics_app())

    @app.exception_handler(MockEngineError)
    async def handle_engine_error(request, exc: MockEngineError):
        return build_error_response(exc, request)

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request, exc: Exception):
        return build_unhandled_response(exc, request)

    return app


app = create_app()
