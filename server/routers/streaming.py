from __future__ import annotations

import asyncio
import contextlib
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import orjson
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from mock_engine.config import get_config_manager
from mock_engine.generators.utils import parse_timestamp_to_microseconds
from mock_engine.observability import websocket_active_connections
from server.logging import get_logger
from server.rate_limiter import AdaptiveRateLimiter

logger = get_logger(__name__)

router = APIRouter(prefix="/v1", tags=["streaming"])

QUEUE_KEY_TEMPLATE = "pregen:{schema}:queue"
BATCH_POP_SIZE = 5000
META_KEY_TEMPLATE = "pregen:{schema}:meta"
USER_STATE_KEY_TEMPLATE = "user_state:{user_id}:{schema}"
GLOBAL_CACHE_COUNT_KEY = "pregen:global:count"  # Global counter across all schemas
GLOBAL_CACHE_SCHEMA_COUNT_KEY = (
    "pregen:{schema}:count"  # Per-schema counter for global tracking
)

_STATEFUL_META: dict[str, dict[str, Any]] = {}
METADATA_CACHE_TTL_SECONDS = 300  # Default: 5 minutes


async def _ensure_stateful_meta(
    redis, schema: str, cache_ttl_seconds: int = METADATA_CACHE_TTL_SECONDS
) -> dict[str, Any]:
    """Load and parse stateful field metadata from Redis with TTL-based caching.

    Args:
        redis: Redis client
        schema: Schema name
        cache_ttl_seconds: TTL for in-memory cache (default: 5 minutes)

    Returns metadata including:
    - fields: List of stateful field configs
    - worker_start_time_seconds: When pre-gen worker started (for wallclock mode)
    """
    if schema in _STATEFUL_META:
        cached_entry = _STATEFUL_META[schema]
        cached_at = cached_entry.get("cached_at", 0)
        if time.time() - cached_at < cache_ttl_seconds:
            return {k: v for k, v in cached_entry.items() if k != "cached_at"}
        else:
            logger.debug("metadata_cache_expired", schema=schema, cached_at=cached_at)
            del _STATEFUL_META[schema]

    meta_key = META_KEY_TEMPLATE.format(schema=schema)
    raw = await redis.get(meta_key)
    if not raw:
        empty_meta = {"fields": [], "worker_start_time_seconds": None}
        _STATEFUL_META[schema] = {**empty_meta, "cached_at": time.time()}
        return empty_meta

    try:
        meta = orjson.loads(raw)
        fields: list[dict[str, Any]] = meta.get("stateful") or []
        worker_start_time_seconds = meta.get("worker_start_time_seconds")
    except Exception:
        fields = []
        worker_start_time_seconds = None

    parsed: list[dict[str, Any]] = []
    for f in fields:
        try:
            field_name = f["field"]
            params = f.get("params") or {}
            start = parse_timestamp_to_microseconds(params.get("start"))
            increment = int(params.get("increment", 1))
            if start is None:
                continue
            kind = (
                "datetime"
                if "datetime" in str(f.get("gen") or f.get("type", "")).lower()
                else "timestamp"
            )
            fmt = params.get("format")
            tz = params.get("tz")
            parsed.append(
                {
                    "field": field_name,
                    "start": start,
                    "increment": increment,
                    "kind": kind,
                    "format": fmt,
                    "tz": tz,
                    "gen": f.get("gen", ""),  # Generator type token
                }
            )
        except Exception:
            continue

    actual_generation_rate = meta.get("actual_generation_rate")
    rate_updated_at = meta.get("rate_updated_at")

    parsed_meta = {
        "fields": parsed,
        "worker_start_time_seconds": worker_start_time_seconds,
        "actual_generation_rate": actual_generation_rate,
        "rate_updated_at": rate_updated_at,
    }
    _STATEFUL_META[schema] = {**parsed_meta, "cached_at": time.time()}
    return parsed_meta


async def _get_or_create_user_state(
    redis, schema: str, user_id: str, meta: dict[str, Any], ttl_seconds: int = 86400
) -> dict[str, int]:
    """Get or create user state with TTL to prevent accumulation.

    Args:
        redis: Redis client
        schema: Schema name
        user_id: User ID for state tracking
        meta: Stateful field metadata
        ttl_seconds: Time-to-live for user state keys (default: 24 hours)

    Returns:
        User state dict mapping field names to last generated values
    """
    state_key = USER_STATE_KEY_TEMPLATE.format(user_id=user_id, schema=schema)
    existing_state = await redis.hgetall(state_key)

    if existing_state:
        parsed_state: dict[str, int] = {}
        for k, v in existing_state.items():
            key = k.decode() if hasattr(k, "decode") else str(k)
            val = int(v.decode() if hasattr(v, "decode") else v)
            parsed_state[key] = val

        # Refresh TTL on existing state
        await redis.expire(state_key, ttl_seconds)
        return parsed_state

    initial_state = {}
    for field_meta in meta.get("fields", []):
        initial_state[field_meta["field"]] = field_meta["start"]

    if initial_state:
        await redis.hset(state_key, mapping=initial_state)
        # Set TTL on new state
        await redis.expire(state_key, ttl_seconds)
    return initial_state


async def _apply_stateful_user_batch(
    items: list[dict[str, Any]],
    user_state: dict[str, int],
    meta: dict[str, Any],
    increment_mode: str = "sequential",
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Apply stateful transformations to batch items.

    Args:
        items: Raw items from Redis queue
        user_state: Per-user state tracking last generated values
        meta: Stateful field metadata
        increment_mode: 'wallclock' or 'sequential'

    Returns:
        Tuple of (transformed items, updated user state)
    """
    fields_meta = meta.get("fields", [])
    if not fields_meta:
        return items, user_state

    new_state = user_state.copy()
    out_items = []
    worker_start_time = meta.get("worker_start_time_seconds")
    current_time_seconds = time.time()

    for item in items:
        payload = item.copy()
        for field_meta in fields_meta:
            field = field_meta["field"]
            increment = field_meta["increment"]
            kind = field_meta["kind"]
            fmt = field_meta.get("format")
            tz = field_meta.get("tz")
            start = field_meta["start"]

            if increment_mode == "wallclock":
                if worker_start_time is not None:
                    elapsed_seconds = current_time_seconds - worker_start_time
                    elapsed_microseconds = int(elapsed_seconds * 1_000_000)
                    increments_passed = elapsed_microseconds // increment
                    new_value = start + (increments_passed * increment)
                else:
                    logger.warning(
                        "wallclock_mode_fallback",
                        field=field,
                        reason="no_worker_start_time",
                    )
                    last_value = new_state.get(field, start)
                    new_value = last_value + increment
                    new_state[field] = new_value
            else:
                last_value = new_state.get(field, start)
                new_value = last_value + increment
                new_state[field] = new_value

            if kind == "datetime":
                dt = datetime.fromtimestamp(new_value / 1_000_000, tz=timezone.utc)
                if tz:
                    try:
                        sign = 1 if tz.startswith("+") else -1
                        hh, mm = tz[1:].split(":")
                        offset = timezone(
                            sign * timedelta(hours=int(hh), minutes=int(mm))
                        )
                        dt = dt.astimezone(offset)
                    except Exception:
                        pass  # Keep UTC if tz is invalid
                payload[field] = dt.strftime(fmt or "%Y-%m-%dT%H:%M:%S%z")
            else:  # timestamp
                payload[field] = new_value

        out_items.append(payload)

    return out_items, new_state


async def _apply_chaos_to_batch(
    items: list[dict[str, Any]],
    schema: str,
    forced_chaos: list[str] | None = None,
) -> tuple[list[dict[str, Any]], list[str], dict[str, Any]]:
    """Apply chaos operations to items individually for better randomness.

    Args:
        items: Items to apply chaos to
        schema: Schema name for chaos tracking
        forced_chaos: Optional list of chaos ops to force apply

    Returns:
        Tuple of (items with chaos applied, chaos descriptions, chaos metadata)
    """
    from mock_engine.context import GenContext
    from mock_engine.chaos.access import get_chaos_manager

    ctx = GenContext()
    ctx.schema_name = schema
    mgr = get_chaos_manager(ctx)

    out_items = []
    all_descriptions = set()
    merged_meta = {}

    if forced_chaos:
        temp_payload = {"items": items}
        result, resp_meta = mgr.apply(
            body=temp_payload, schema_name=schema, forced_activation=forced_chaos
        )
        body_items = getattr(result, "body", {}).get("items", items)
        descriptions = getattr(result, "descriptions", []) or []
        return body_items, descriptions, resp_meta or {}
    else:
        for item in items:
            temp_payload = {"items": [item]}
            result, resp_meta = mgr.apply(
                body=temp_payload, schema_name=schema, forced_activation=None
            )

            body_items = getattr(result, "body", {}).get("items", [item])
            descriptions = getattr(result, "descriptions", []) or []

            out_items.append(body_items[0] if body_items else item)

            all_descriptions.update(descriptions)

            if resp_meta:
                merged_meta.update(resp_meta)

        return out_items, sorted(all_descriptions), merged_meta


async def _save_user_state(
    redis, schema: str, user_id: str, state: dict[str, int], ttl_seconds: int = 86400
):
    """Save user state with TTL to prevent accumulation.

    Args:
        redis: Redis client
        schema: Schema name
        user_id: User ID
        state: State dict to save
        ttl_seconds: Time-to-live for user state keys (default: 24 hours)
    """
    if not state:
        return
    state_key = USER_STATE_KEY_TEMPLATE.format(user_id=user_id, schema=schema)
    await redis.hset(state_key, mapping=state)
    await redis.expire(state_key, ttl_seconds)


def _generate_live_batch(schema: str, count: int) -> list[dict[str, Any]]:
    """Generate batch of items live (fallback when cache is empty).

    Args:
        schema: Schema name
        count: Number of items to generate

    Returns:
        List of generated items
    """
    from mock_engine.context import GenContext
    from server.deps import get_generator

    try:
        gen = get_generator(schema)
        ctx = GenContext(seed=None)  # Random seed for live generation
        ctx.schema_name = schema

        items = [gen.generate(ctx) for _ in range(count)]
        logger.debug("live_generation_batch", schema=schema, count=len(items))
        return items
    except Exception as e:
        logger.error(
            "live_generation_failed", schema=schema, error=str(e), exc_info=True
        )
        return []


async def _update_global_cache_count(redis, schema: str, delta: int):
    """Update global cache counter when items are consumed or added.

    Args:
        redis: Redis client
        schema: Schema name
        delta: Change in count (negative for consumption, positive for addition)
    """
    try:
        await redis.incrby(GLOBAL_CACHE_COUNT_KEY, delta)

        schema_count_key = GLOBAL_CACHE_SCHEMA_COUNT_KEY.format(schema=schema)
        new_count = await redis.incrby(schema_count_key, delta)

        if new_count < 0:
            await redis.set(schema_count_key, 0)
            logger.warning("schema_count_negative_reset", schema=schema, was=new_count)
    except Exception as e:
        logger.warning(
            "global_count_update_failed", schema=schema, delta=delta, error=str(e)
        )


@router.websocket("/schemas/{schema}/stream")
async def stream_schema(
    websocket: WebSocket,
    schema: str,
    duration: int | None = None,
    max_events: int | None = None,
    user_id: str | None = None,
    forced_chaos: str | None = None,
):
    """WebSocket streaming endpoint for pre-generated data.

    Args:
        schema: Schema name to stream
        duration: Maximum stream duration in seconds
        max_events: Maximum number of events to send
        user_id: Optional user ID for stateful continuation. If not provided, generates random ID.
                 If provided and exists, continues from saved state (only works with sequential mode).
        forced_chaos: Optional comma-separated list of chaos ops to force for this stream.
    """
    await websocket.accept()

    websocket_active_connections.labels(schema=schema).inc()

    try:
        cm = get_config_manager()
        batch_retention = cm.get_value("server.streaming.batch_retention")
        increment_mode = cm.get_value("server.streaming.increment_mode", "sequential")
        apply_chaos = cm.get_value("server.streaming.apply_chaos_in_consumer", True)
        allow_forced_chaos = cm.get_value("server.streaming.allow_forced_chaos", True)
        user_state_ttl = cm.get_value("server.streaming.user_state_ttl_seconds", 86400)
        metadata_cache_ttl = cm.get_value(
            "server.streaming.metadata_cache_ttl_seconds", 300
        )

        rate_limit_enabled = cm.get_value("server.streaming.rate_limit_enabled", False)
        base_rate = cm.get_value("server.streaming.base_rate", 1000)
        auto_detect_rate = cm.get_value("server.streaming.auto_detect_rate", False)
        auto_detect_sample_size = cm.get_value(
            "server.streaming.auto_detect_sample_size", 1000
        )

        pregen_enabled = cm.get_value("server.pregeneration.enabled", True)
        fallback_to_live = cm.get_value("server.pregeneration.fallback_to_live", True)
        require_cache = cm.get_value("server.pregeneration.require_cache", False)
        global_max_items = cm.get_value("server.pregeneration.global_max_items", None)
    except Exception:
        batch_retention = False
        increment_mode = "sequential"
        apply_chaos = True
        allow_forced_chaos = True
        user_state_ttl = 86400
        metadata_cache_ttl = 300
        rate_limit_enabled = False
        base_rate = 1000
        auto_detect_rate = False
        auto_detect_sample_size = 1000
        pregen_enabled = True
        fallback_to_live = True
        require_cache = False
        global_max_items = None

    redis = websocket.app.state.redis
    queue_key = QUEUE_KEY_TEMPLATE.format(schema=schema)
    stateful_meta = await _ensure_stateful_meta(
        redis, schema, cache_ttl_seconds=metadata_cache_ttl
    )

    if not user_id:
        user_id = uuid.uuid4().hex
        logger.info(
            "assigned_random_user_id",
            user_id=user_id,
            schema=schema,
            increment_mode=increment_mode,
        )
    else:
        if increment_mode == "sequential":
            state_key = USER_STATE_KEY_TEMPLATE.format(user_id=user_id, schema=schema)
            existing_state = await redis.hgetall(state_key)
            if existing_state:
                logger.info(
                    "resuming_user_state",
                    user_id=user_id,
                    schema=schema,
                    increment_mode=increment_mode,
                )
            else:
                logger.info(
                    "creating_new_user_state",
                    user_id=user_id,
                    schema=schema,
                    increment_mode=increment_mode,
                )
        else:
            logger.info(
                "user_id_provided_but_wallclock_mode",
                user_id=user_id,
                schema=schema,
                increment_mode=increment_mode,
            )

    if increment_mode == "sequential":
        user_state = await _get_or_create_user_state(
            redis, schema, user_id, stateful_meta, ttl_seconds=user_state_ttl
        )
    else:
        user_state = {}

    forced_chaos_list: list[str] | None = None
    if forced_chaos and allow_forced_chaos:
        forced_chaos_list = [op.strip() for op in forced_chaos.split(",") if op.strip()]
    elif forced_chaos:
        logger.info("forced_chaos_blocked_by_config", schema=schema)

    rate_limiter: AdaptiveRateLimiter | None = None
    if rate_limit_enabled:
        effective_rate = base_rate
        if auto_detect_rate:
            worker_rate = stateful_meta.get("actual_generation_rate")
            if worker_rate and worker_rate > 0:
                effective_rate = worker_rate
                logger.info(
                    "using_worker_generation_rate",
                    schema=schema,
                    worker_rate=worker_rate,
                    base_rate=base_rate,
                )

        rate_limiter = AdaptiveRateLimiter(
            base_rate=effective_rate,
            auto_detect=False,
            auto_detect_sample_size=auto_detect_sample_size,
        )
        logger.info(
            "rate_limiter_enabled",
            schema=schema,
            effective_rate=effective_rate,
            auto_detect_from_worker=auto_detect_rate,
        )

    stream_mode = "pregen_redis" if pregen_enabled else "live"
    if pregen_enabled and fallback_to_live:
        stream_mode = "pregen_with_fallback"

    await websocket.send_json(
        {
            "type": "start",
            "schema": schema,
            "user_id": user_id,
            "mode": stream_mode,
            "increment_mode": increment_mode,
            "forced_chaos": forced_chaos_list,
            "rate_limit_enabled": rate_limit_enabled,
            "rate_limit_base": base_rate if rate_limit_enabled else None,
        }
    )

    seq = 0
    start_time = time.time()

    try:
        while True:
            now = time.time()
            if duration and (now - start_time) >= duration:
                break
            if max_events is not None and seq >= max_events:
                break

            remaining = max_events - seq if max_events is not None else None
            if remaining is not None and remaining <= 0:
                break
            pop_size = min(BATCH_POP_SIZE, remaining) if remaining else BATCH_POP_SIZE

            if rate_limiter and not await rate_limiter.consume(pop_size):
                await asyncio.sleep(0.001)
                continue

            raw_items: list[dict[str, Any]] = []
            used_live_generation = False

            if pregen_enabled:
                batch_bytes = await redis.lpop(queue_key, pop_size)
                if batch_bytes:
                    raw_items = [orjson.loads(b) for b in batch_bytes]
                    if global_max_items is not None:
                        await _update_global_cache_count(redis, schema, -len(raw_items))
                elif fallback_to_live:
                    logger.info(
                        "cache_empty_fallback_to_live", schema=schema, pop_size=pop_size
                    )
                    raw_items = _generate_live_batch(schema, pop_size)
                    used_live_generation = True
                elif require_cache:
                    error_msg = {
                        "type": "error",
                        "error": "CacheRequired",
                        "message": "Pre-generation cache is empty",
                    }
                    await websocket.send_json(error_msg)
                    break
                else:
                    await asyncio.sleep(0.01)
                    continue
            else:
                raw_items = _generate_live_batch(schema, pop_size)
                used_live_generation = True

            if not raw_items:
                await asyncio.sleep(0.01)
                continue

            batch_items, user_state = await _apply_stateful_user_batch(
                raw_items, user_state, stateful_meta, increment_mode=increment_mode
            )

            chaos_descriptions: list[str] = []
            chaos_meta: dict[str, Any] = {}
            if apply_chaos:
                try:
                    (
                        batch_items,
                        chaos_descriptions,
                        chaos_meta,
                    ) = await _apply_chaos_to_batch(
                        batch_items, schema, forced_chaos=forced_chaos_list
                    )

                    if (
                        rate_limiter
                        and chaos_meta.get("burst_active")
                        and not forced_chaos_list
                    ):
                        burst_rate = chaos_meta.get("burst_rate", base_rate * 10)
                        burst_duration = chaos_meta.get("burst_duration", 10)
                        required_cache_items = chaos_meta.get(
                            "required_cache_items", burst_rate * burst_duration
                        )

                        if pregen_enabled and required_cache_items:
                            current_queue_len = await redis.llen(queue_key)
                            if current_queue_len < required_cache_items:
                                logger.warning(
                                    "burst_blocked_insufficient_cache",
                                    schema=schema,
                                    required=required_cache_items,
                                    available=current_queue_len,
                                    burst_rate=burst_rate,
                                    burst_duration=burst_duration,
                                )
                            else:
                                rate_limiter.activate_burst(burst_rate, burst_duration)
                                logger.info(
                                    "burst_activated_cache_validated",
                                    schema=schema,
                                    required=required_cache_items,
                                    available=current_queue_len,
                                    burst_rate=burst_rate,
                                    burst_duration=burst_duration,
                                )
                        else:
                            rate_limiter.activate_burst(burst_rate, burst_duration)
                except Exception as chaos_err:
                    logger.error(
                        "chaos_apply_failed",
                        schema=schema,
                        error=str(chaos_err),
                        forced_chaos=forced_chaos_list,
                    )

            sent_in_batch = 0
            try:
                for batch_item in batch_items:
                    if max_events is not None and seq >= max_events:
                        break
                    msg = {
                        "type": "event",
                        "seq": seq,
                        "data": batch_item,
                    }
                    if chaos_descriptions:
                        msg["chaos_applied"] = chaos_descriptions
                    if chaos_meta:
                        msg["chaos_meta"] = chaos_meta
                    await websocket.send_json(msg)
                    seq += 1
                    sent_in_batch += 1
            except WebSocketDisconnect:
                if batch_retention:
                    unsent_items = raw_items[sent_in_batch:]
                    if unsent_items:
                        unsent_bytes = [orjson.dumps(item) for item in unsent_items]
                        await redis.lpush(queue_key, *unsent_bytes)
                        logger.info(
                            "pushed_back_unsent_items",
                            count=len(unsent_items),
                            user_id=user_id,
                        )
                raise

            if increment_mode == "sequential":
                await _save_user_state(
                    redis, schema, user_id, user_state, ttl_seconds=user_state_ttl
                )

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(
            "stream_unexpected_error", error=str(e), schema=schema, user_id=user_id
        )
        error_msg = {"type": "error", "error": type(e).__name__, "message": str(e)}
        with contextlib.suppress(Exception):
            await websocket.send_json(error_msg)
    finally:
        websocket_active_connections.labels(schema=schema).dec()

        if increment_mode == "sequential":
            await _save_user_state(
                redis, schema, user_id, user_state, ttl_seconds=user_state_ttl
            )
        with contextlib.suppress(Exception):
            await websocket.close()
