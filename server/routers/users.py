"""User state management endpoints.

Provides REST API for managing user states stored in Redis for stateful streaming.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from server.deps import get_redis
from server.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/users", tags=["users"])

USER_STATE_KEY_PREFIX = "user_state:"


@router.get("")
async def list_users(
    schema: str | None = None,
    redis=Depends(get_redis),
) -> JSONResponse:
    """List all users with state in Redis.

    Args:
        schema: Optional schema filter to list only users for specific schema

    Returns:
        JSONResponse with user list and count
    """
    if schema:
        pattern = f"{USER_STATE_KEY_PREFIX}*:{schema}"
    else:
        pattern = f"{USER_STATE_KEY_PREFIX}*"

    keys = await redis.keys(pattern)

    users_data = []
    seen_users = set()

    for key_bytes in keys:
        key = key_bytes.decode() if isinstance(key_bytes, bytes) else key_bytes
        parts = key.split(":")
        if len(parts) >= 3:
            user_id = parts[1]
            schema_name = parts[2]

            if user_id not in seen_users or not schema:
                seen_users.add(user_id)
                # Get TTL
                ttl = await redis.ttl(key)

                users_data.append({
                    "user_id": user_id,
                    "schema": schema_name,
                    "ttl_seconds": ttl if ttl > 0 else None,
                })

    if not schema:
        user_map: dict[str, dict[str, Any]] = {}
        for user_data in users_data:
            user_id = user_data["user_id"]
            if user_id not in user_map:
                user_map[user_id] = {
                    "user_id": user_id,
                    "schemas": [],
                }
            user_map[user_id]["schemas"].append({
                "schema": user_data["schema"],
                "ttl_seconds": user_data["ttl_seconds"],
            })

        return JSONResponse({
            "users": list(user_map.values()),
            "count": len(user_map),
        })

    return JSONResponse({
        "users": users_data,
        "count": len(users_data),
    })


@router.get("/{user_id}")
async def get_user(
    user_id: str,
    redis=Depends(get_redis),
) -> JSONResponse:
    """Get user state across all schemas.

    Args:
        user_id: User ID to retrieve

    Returns:
        JSONResponse with user state data
    """
    pattern = f"{USER_STATE_KEY_PREFIX}{user_id}:*"
    keys = await redis.keys(pattern)

    if not keys:
        raise HTTPException(status_code=404, detail=f"User '{user_id}' not found")

    schemas_data = []

    for key_bytes in keys:
        key = key_bytes.decode() if isinstance(key_bytes, bytes) else key_bytes
        parts = key.split(":")
        if len(parts) >= 3:
            schema_name = parts[2]

            state_raw = await redis.hgetall(key)
            state = {}
            for field, value in state_raw.items():
                field_name = field.decode() if isinstance(field, bytes) else field
                field_value = int(value.decode() if isinstance(value, bytes) else value)
                state[field_name] = field_value

            ttl = await redis.ttl(key)

            schemas_data.append({
                "schema": schema_name,
                "state": state,
                "ttl_seconds": ttl if ttl > 0 else None,
            })

    return JSONResponse({
        "user_id": user_id,
        "schemas": schemas_data,
        "count": len(schemas_data),
    })


@router.get("/{user_id}/schemas/{schema}")
async def get_user_schema_state(
    user_id: str,
    schema: str,
    redis=Depends(get_redis),
) -> JSONResponse:
    """Get user state for specific schema.

    Args:
        user_id: User ID
        schema: Schema name

    Returns:
        JSONResponse with state data
    """
    key = f"{USER_STATE_KEY_PREFIX}{user_id}:{schema}"

    state_raw = await redis.hgetall(key)

    if not state_raw:
        raise HTTPException(
            status_code=404,
            detail=f"No state found for user '{user_id}' and schema '{schema}'"
        )

    state = {}
    for field, value in state_raw.items():
        field_name = field.decode() if isinstance(field, bytes) else field
        field_value = int(value.decode() if isinstance(value, bytes) else value)
        state[field_name] = field_value

    ttl = await redis.ttl(key)

    return JSONResponse({
        "user_id": user_id,
        "schema": schema,
        "state": state,
        "ttl_seconds": ttl if ttl > 0 else None,
    })


@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    redis=Depends(get_redis),
) -> JSONResponse:
    """Delete all state for a user across all schemas.

    Args:
        user_id: User ID to delete

    Returns:
        JSONResponse with deletion count
    """
    pattern = f"{USER_STATE_KEY_PREFIX}{user_id}:*"
    keys = await redis.keys(pattern)

    if not keys:
        raise HTTPException(status_code=404, detail=f"User '{user_id}' not found")

    deleted = await redis.delete(*keys)

    logger.info("user_deleted", user_id=user_id, keys_deleted=deleted)

    return JSONResponse({
        "user_id": user_id,
        "deleted": deleted,
        "message": f"Deleted state for user '{user_id}' across {deleted} schema(s)",
    })


@router.delete("/{user_id}/schemas/{schema}")
async def delete_user_schema_state(
    user_id: str,
    schema: str,
    redis=Depends(get_redis),
) -> JSONResponse:
    """Delete user state for specific schema.

    Args:
        user_id: User ID
        schema: Schema name

    Returns:
        JSONResponse with deletion confirmation
    """
    key = f"{USER_STATE_KEY_PREFIX}{user_id}:{schema}"

    deleted = await redis.delete(key)

    if deleted == 0:
        raise HTTPException(
            status_code=404,
            detail=f"No state found for user '{user_id}' and schema '{schema}'"
        )

    logger.info("user_schema_deleted", user_id=user_id, schema=schema)

    return JSONResponse({
        "user_id": user_id,
        "schema": schema,
        "message": f"Deleted state for user '{user_id}' and schema '{schema}'",
    })
