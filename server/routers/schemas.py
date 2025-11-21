from __future__ import annotations

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse
from mock_engine.context import GenContext
from mock_engine.chaos.access import get_chaos_manager
from server.deps import get_generator

router = APIRouter(prefix="/v1", tags=["schemas"])

@router.get("/schemas/{name}/generate")
async def generate_schema(
    name: str,
    request: Request,
    count: int = Query(1, ge=1, le=1000),
    seed: int | None = Query(None),
    chaos_ops: str | None = Query(None, description="Comma-separated chaos op keys to force"),
) -> JSONResponse:
    # TODO(service): move generator+context plumbing into deps/service layer.
    gen = get_generator(name)
    ctx = GenContext(seed=seed)
    ctx.schema_name = name
    items = [gen.generate(ctx) for _ in range(count)]
    payload: dict = {"items": items, "count": len(items)}

    forced = None
    if chaos_ops:
        forced = [op.strip() for op in chaos_ops.split(",") if op.strip()]

    mgr = get_chaos_manager(ctx)
    result, meta = mgr.apply(body=payload, schema_name=name, forced_activation=forced or None)
    payload = getattr(result, "body", payload) or payload
    descriptions = getattr(result, "descriptions", None) or []
    try:
        if isinstance(payload, dict) and "count" not in payload and "items" in payload:
            payload["count"] = len(payload["items"])
    except Exception:
        pass
    if descriptions and isinstance(payload, dict):
        payload = dict(payload)
        payload["chaos_descriptions"] = descriptions

    status_override = (meta or {}).get("status")
    headers_override = (meta or {}).get("headers")
    return JSONResponse(payload, status_code=status_override or 200, headers=headers_override or None)
