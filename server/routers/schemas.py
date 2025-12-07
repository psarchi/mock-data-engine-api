from __future__ import annotations

import time

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse
from mock_engine.context import GenContext
from mock_engine.chaos.access import get_chaos_manager
from mock_engine.observability import (
    generation_duration_seconds,
    items_generated_total,
    seed_source_total,
    chaos_op_executions_total,
    chaos_items_affected_total,
    chaos_op_duration_seconds,
    get_count_bucket,
)
from server.deps import get_generator
from server.logging import get_logger
from server.metadata import build_response_with_metadata

logger = get_logger(__name__)

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
    start_time = time.perf_counter()

    logger.debug(
        "generation_request_received",
        schema=name,
        count=count,
        seed=seed,
        chaos_ops=chaos_ops,
        include_metadata=include_metadata
    )

    if seed is not None:
        seed_source_total.labels(source='user_provided').inc()
    else:
        seed_source_total.labels(source='server_generated').inc()

    gen = get_generator(name)
    ctx = GenContext(seed=seed)
    ctx.schema_name = name

    count_bucket = get_count_bucket(count)
    gen_start = time.perf_counter()
    items = [gen.generate(ctx) for _ in range(count)]
    gen_duration = time.perf_counter() - gen_start

    generation_duration_seconds.labels(
        schema=name,
        count_bucket=count_bucket
    ).observe(gen_duration)

    items_generated_total.labels(schema=name).inc(len(items))

    forced = None
    if chaos_ops:
        forced = [op.strip() for op in chaos_ops.split(",") if op.strip()]

    mgr = get_chaos_manager(ctx)
    temp_payload = {"items": items}

    chaos_start = time.perf_counter()
    result, meta = mgr.apply(body=temp_payload, schema_name=name, forced_activation=forced or None)
    chaos_duration = time.perf_counter() - chaos_start

    items = getattr(result, "body", {}).get("items", items) if hasattr(result, "body") else items
    descriptions = getattr(result, "descriptions", [])

    for desc in descriptions:
        op_name = desc.split("(")[0] if "(" in desc else desc

        chaos_op_executions_total.labels(
            op=op_name,
            schema=name,
            applied='true'
        ).inc()

        if descriptions:
            chaos_op_duration_seconds.labels(
                op=op_name,
                schema=name
            ).observe(chaos_duration / len(descriptions))

        if " items)" in desc:
            try:
                affected = int(desc.split("(")[1].split(" ")[0])
                chaos_items_affected_total.labels(
                    op=op_name,
                    schema=name
                ).inc(affected)
            except (ValueError, IndexError):
                pass

    payload = build_response_with_metadata(
        items=items,
        context=ctx,
        chaos_results=descriptions,
        include_metadata=include_metadata,
    )

    duration_ms = (time.perf_counter() - start_time) * 1000

    logger.info(
        "generation_complete",
        schema=name,
        count=len(items),
        duration_ms=round(duration_ms, 2),
        chaos_count=len(descriptions)
    )

    logger.debug(
        "generation_details",
        seed=ctx.seed,
        chaos_applied=descriptions
    )

    status_override = (meta or {}).get("status")
    headers_override = (meta or {}).get("headers")
    return JSONResponse(payload, status_code=status_override or 200, headers=headers_override or None)
