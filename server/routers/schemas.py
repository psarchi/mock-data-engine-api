from __future__ import annotations

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse
from mock_engine.context import GenContext
from mock_engine.chaos.access import get_chaos_manager
from server.deps import get_generator
from server.metadata import build_response_with_metadata

router = APIRouter(prefix="/v1", tags=["schemas"])

@router.get("/schemas/{name}/generate")
async def generate_schema(
    name: str,
    request: Request,
    count: int = Query(1, ge=1, le=1000),
    seed: int | None = Query(None),
    chaos_ops: str | None = Query(None, description="Comma-separated chaos op keys to force"),
    include_metadata: bool = Query(False, description="Include _metadata field in response"),
) -> JSONResponse:
    # TODO(service): move generator+context plumbing into deps/service layer.
    gen = get_generator(name)
    ctx = GenContext(seed=seed)
    ctx.schema_name = name
    items = [gen.generate(ctx) for _ in range(count)]

    forced = None
    if chaos_ops:
        forced = [op.strip() for op in chaos_ops.split(",") if op.strip()]

    mgr = get_chaos_manager(ctx)
    temp_payload = {"items": items}
    result, meta = mgr.apply(body=temp_payload, schema_name=name, forced_activation=forced or None)

    items = getattr(result, "body", {}).get("items", items) if hasattr(result, "body") else items
    descriptions = getattr(result, "descriptions", [])

    payload = build_response_with_metadata(
        items=items,
        context=ctx,
        chaos_results=descriptions,
        include_metadata=include_metadata,
    )

    status_override = (meta or {}).get("status")
    headers_override = (meta or {}).get("headers")
    return JSONResponse(payload, status_code=status_override or 200, headers=headers_override or None)
