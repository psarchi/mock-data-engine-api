from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from server.auth import RequireAuth
from server.deps import get_correlation_redis

router = APIRouter(prefix="/v1/admin/pools", tags=["admin-pools"])


@router.delete("/{schema_name}")
def flush_pool(
    schema_name: str,
    _token: RequireAuth = None,
    redis=Depends(get_correlation_redis),
) -> dict[str, Any]:
    """Delete the pool for a schema from Redis.

    Use this when you want to regenerate a schema from scratch without
    nuking the whole Redis instance. Downstream schemas that depend on
    this pool will start returning 422 until you repopulate it.

    Args:
        schema_name: The schema whose pool to delete (e.g. ``appointment``
            deletes ``pool:appointment``).

    Returns:
        Confirmation with the deleted key and number of records removed.
    """
    if redis is None:
        raise HTTPException(status_code=503, detail="Redis not available")

    pool_key = f"pool:{schema_name}"
    size = redis.scard(pool_key)
    deleted = redis.delete(pool_key)

    return {
        "deleted": bool(deleted),
        "key": pool_key,
        "records_removed": size,
    }


@router.get("/{schema_name}")
def get_pool_info(
    schema_name: str,
    _token: RequireAuth = None,
    redis=Depends(get_correlation_redis),
) -> dict[str, Any]:
    """Get info about a pool without modifying it.

    Args:
        schema_name: The schema whose pool to inspect.

    Returns:
        Pool key, record count, and a sample record (if the pool is non-empty).
    """
    if redis is None:
        raise HTTPException(status_code=503, detail="Redis not available")

    import json

    pool_key = f"pool:{schema_name}"
    size = redis.scard(pool_key)
    sample_raw = redis.srandmember(pool_key) if size else None
    sample = json.loads(sample_raw) if sample_raw else None

    return {
        "key": pool_key,
        "size": size,
        "sample": sample,
    }


@router.delete("/")
def flush_all_pools(
    _token: RequireAuth = None,
    redis=Depends(get_correlation_redis),
) -> dict[str, Any]:
    """Delete all pool keys from Redis.

    Finds every key matching ``pool:*`` and deletes them all. Use with care —
    all downstream schemas will start returning 422 until pools are repopulated.

    Returns:
        Number of pool keys deleted.
    """
    if redis is None:
        raise HTTPException(status_code=503, detail="Redis not available")

    keys = redis.keys("pool:*")
    if not keys:
        return {"deleted": 0, "keys": []}

    count = redis.delete(*keys)
    return {
        "deleted": count,
        "keys": [k if isinstance(k, str) else k.decode() for k in keys],
    }
