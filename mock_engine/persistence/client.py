"""Redis and PostgreSQL clients for persistence."""
from __future__ import annotations

import json
import os
from typing import Any

import asyncpg
import redis.asyncio as redis
from datetime import datetime, timedelta, timezone

from mock_engine.persistence.errors import (
    RedisConnectionError,
    RedisWriteError,
    RedisReadError,
    PostgresConnectionError,
    PostgresWriteError,
    PostgresReadError,
    DataSerializationError,
)


class RedisClient:
    """Async Redis client for caching."""

    def __init__(self, url: str | None = None, key_prefix: str = "data:"):
        self.url = url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.key_prefix = key_prefix
        self._client: redis.Redis | None = None

    async def connect(self) -> None:
        """Establish Redis connection."""
        if self._client is None:
            try:
                self._client = await redis.from_url(self.url, decode_responses=True)
            except Exception as e:
                raise RedisConnectionError(f"Failed to connect to Redis at {self.url}: {e}") from e

    async def close(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.close()

    def _make_key(self, id: str) -> str:
        """Create prefixed key."""
        return f"{self.key_prefix}{id}"

    async def set(
        self,
        id: str,
        data: dict[str, Any],
        ttl_hours: int = 24
    ) -> bool:
        """Store dataset in Redis with TTL.

        Args:
            id: Dataset ID
            data: Dataset data to store
            ttl_hours: Time-to-live in hours

        Returns:
            True if successful
        """
        if not self._client:
            await self.connect()

        if not self._client:
            raise RedisConnectionError("Redis client not initialized")

        try:
            key = self._make_key(id)
            value = json.dumps(data)
            ttl_seconds = ttl_hours * 3600
            await self._client.set(key, value, ex=ttl_seconds)
            return True
        except (TypeError, ValueError) as e:
            raise DataSerializationError(f"Failed to serialize data for {id}: {e}") from e
        except Exception as e:
            raise RedisWriteError(f"Failed to write to Redis key {id}: {e}") from e

    async def get(self, id: str) -> dict[str, Any] | None:
        """Retrieve dataset from Redis.

        Args:
            id: Dataset ID

        Returns:
            Dataset data or None if not found
        """
        if not self._client:
            await self.connect()

        if not self._client:
            raise RedisConnectionError("Redis client not initialized")

        try:
            key = self._make_key(id)
            value = await self._client.get(key)

            if value:
                return json.loads(value)
            return None
        except (TypeError, ValueError, json.JSONDecodeError) as e:
            raise DataSerializationError(f"Failed to deserialize data for {id}: {e}") from e
        except Exception as e:
            raise RedisReadError(f"Failed to read from Redis key {id}: {e}") from e

    async def delete(self, id: str) -> bool:
        """Delete dataset from Redis.

        Args:
            id: Dataset ID

        Returns:
            True if deleted, False if not found
        """
        if not self._client:
            await self.connect()

        key = self._make_key(id)
        result = await self._client.delete(key)
        return result > 0

    async def keys(self, pattern: str = "*") -> list[str]:
        """Get all keys matching pattern.

        Args:
            pattern: Redis key pattern (default: "*")

        Returns:
            List of matching keys
        """
        if not self._client:
            await self.connect()

        full_pattern = f"{self.key_prefix}{pattern}"
        keys = await self._client.keys(full_pattern)
        return [k.replace(self.key_prefix, "") for k in keys]


class PostgresClient:
    """Async PostgreSQL client for long-term storage."""

    def __init__(self, url: str | None = None):
        self.url = url or os.getenv(
            "DATABASE_URL",
            "postgresql://mock_user:mock_pass@localhost:5432/mock_engine"
        )
        self._pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        """Establish PostgreSQL connection pool."""
        if self._pool is None:
            try:
                self._pool = await asyncpg.create_pool(self.url, min_size=5, max_size=10)
            except Exception as e:
                raise PostgresConnectionError(f"Failed to connect to PostgreSQL at {self.url}: {e}") from e

    async def close(self) -> None:
        """Close PostgreSQL connection pool."""
        if self._pool:
            await self._pool.close()

    async def insert(
        self,
        id: str,
        schema_name: str,
        data: dict[str, Any],
        metadata: dict[str, Any] | None = None,
        seed: int | None = None,
        chaos_applied: list[str] | None = None,
        retention_days: int = 30,
    ) -> bool:
        """Insert dataset into PostgreSQL.

        Args:
            id: Dataset ID
            schema_name: Schema name
            data: Dataset data
            metadata: Optional metadata
            seed: Optional seed value
            chaos_applied: Optional list of chaos ops
            retention_days: Days before expiration

        Returns:
            True if successful
        """
        if not self._pool:
            await self.connect()

        if not self._pool:
            raise PostgresConnectionError("PostgreSQL connection pool not initialized")

        try:
            expires_at = datetime.now(timezone.utc) + timedelta(days=retention_days)

            query = """
                INSERT INTO datasets
                (id, schema_name, data, metadata, seed, chaos_applied, expires_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (id) DO NOTHING
            """

            async with self._pool.acquire() as conn:
                await conn.execute(
                    query,
                    id,
                    schema_name,
                    json.dumps(data),
                    json.dumps(metadata) if metadata else None,
                    str(seed) if seed is not None else None,
                    chaos_applied,
                    expires_at,
                )

            return True
        except (TypeError, ValueError) as e:
            raise DataSerializationError(f"Failed to serialize data for {id}: {e}") from e
        except Exception as e:
            raise PostgresWriteError(f"Failed to insert dataset {id} into PostgreSQL: {e}") from e

    async def get(self, id: str) -> dict[str, Any] | None:
        """Retrieve dataset from PostgreSQL.

        Args:
            id: Dataset ID

        Returns:
            Dataset record or None if not found
        """
        if not self._pool:
            await self.connect()

        query = """
            SELECT id, schema_name, data, metadata, seed, chaos_applied,
                   created_at, expires_at
            FROM datasets
            WHERE id = $1 AND expires_at > NOW()
        """

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(query, id)

        if row:
            return {
                "id": row["id"],
                "schema_name": row["schema_name"],
                "data": json.loads(row["data"]),
                "metadata": json.loads(row["metadata"]) if row["metadata"] else None,
                "seed": row["seed"],
                "chaos_applied": row["chaos_applied"],
                "created_at": row["created_at"],
                "expires_at": row["expires_at"],
            }

        return None

    async def delete(self, id: str) -> bool:
        """Delete dataset from PostgreSQL.

        Args:
            id: Dataset ID

        Returns:
            True if deleted, False if not found
        """
        if not self._pool:
            await self.connect()

        query = "DELETE FROM datasets WHERE id = $1"

        async with self._pool.acquire() as conn:
            result = await conn.execute(query, id)

        return "DELETE 1" in result

    async def cleanup_expired(self) -> int:
        """Delete expired datasets.

        Returns:
            Number of deleted records
        """
        if not self._pool:
            await self.connect()

        query = "SELECT cleanup_expired_datasets()"

        async with self._pool.acquire() as conn:
            result = await conn.fetchval(query)

        return result or 0

    async def find_missing_ids(self, redis_ids: list[str]) -> list[str]:
        """Find IDs that exist in Redis but not in PostgreSQL.

        Args:
            redis_ids: List of IDs from Redis

        Returns:
            List of IDs missing in PostgreSQL
        """
        if not self._pool or not redis_ids:
            return []

        query = """
            SELECT id FROM datasets
            WHERE id = ANY($1::text[])
        """

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, redis_ids)

        existing_ids = {row["id"] for row in rows}
        return [id for id in redis_ids if id not in existing_ids]
