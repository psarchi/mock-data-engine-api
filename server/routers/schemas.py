from __future__ import annotations

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/v1", tags=["schemas"])

@router.get("/schemas/{name}/generate")
async def generate_schema(name: str, request: Request, count: int = Query(1, ge=1, le=1000), seed: int | None = Query(None)) -> JSONResponse:
    # placeholder
    pass
