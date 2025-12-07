from __future__ import annotations

import uuid
from contextvars import ContextVar
from typing import Callable

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


request_id_var: ContextVar[str] = ContextVar("request_id", default=None)


class CorrelationMiddleware(BaseHTTPMiddleware):
    """Middleware to track request correlation IDs.

    Extracts or generates a unique request ID for each request and:
    1. Stores it in a context variable for application code access
    2. Binds it to structlog context for automatic inclusion in logs
    3. Adds it to response headers for client correlation

    The request ID can be provided by clients via X-Request-ID header,
    or will be auto-generated if not present.
    """

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        """Process request with correlation ID tracking.

        Args:
            request: Incoming FastAPI request.
            call_next: Next middleware/handler in chain.

        Returns:
            Response: Response with X-Request-ID header added.
        """
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = str(uuid.uuid4())

        request_id_var.set(request_id)

        structlog.contextvars.bind_contextvars(request_id=request_id)

        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id

            return response
        finally:
            structlog.contextvars.clear_contextvars()


def get_request_id() -> str | None:
    """Get the current request correlation ID.

    Returns:
        str | None: Current request ID, or None if not in request context.
    """
    return request_id_var.get()
