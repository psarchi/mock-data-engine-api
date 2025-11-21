from __future__ import annotations

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse
from mock_engine.context import GenContext
from server.deps import get_generator

router = APIRouter(prefix="/v1", tags=["schemas"])

@router.get("/schemas/{name}/generate")
async def generate_schema(name: str, request: Request, count: int = Query(1, ge=1, le=1000), seed: int | None = Query(None)) -> JSONResponse:
    # TODO(service): move generator+context plumbing into deps/service layer.
    gen = get_generator(name)
    ctx = GenContext(seed=seed)
    ctx.schema_name = name
    items = [gen.generate(ctx) for _ in range(count)]
    return JSONResponse({"items": items, "count": len(items)})
