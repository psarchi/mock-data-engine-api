from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from mock_engine.persistence import StorageManager
from server.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/v1", tags=["data"])


@router.get("/data/{id}")
async def retrieve_dataset_metadata(id: str) -> JSONResponse:
    """Retrieve dataset metadata (lightweight, no items).

    Checks Redis (hot cache) first, then PostgreSQL (warm storage).
    Returns 404 if not found or expired.

    For full items, use GET /data/{id}/items

    Args:
        id: Dataset ID

    Returns:
        Dataset metadata without items
    """
    storage = StorageManager()
    await storage.connect()

    try:
        metadata = await storage.retrieve_metadata(id)

        if not metadata:
            raise HTTPException(
                status_code=404,
                detail=f"Dataset '{id}' not found or expired (30-day retention)",
            )

        response = {
            "id": metadata.id,
            "schema": metadata.schema_name,
            "seed": metadata.seed,
            "count": metadata.count,
            "chaos_applied": metadata.chaos_applied or [],
            "created_at": metadata.created_at.isoformat(),
            "expires_at": metadata.expires_at.isoformat(),
        }

        logger.info("metadata_retrieved", id=id, schema=metadata.schema_name)

        return JSONResponse(response)

    finally:
        await storage.close()


@router.get("/data/{id}/items")
async def retrieve_dataset_items(id: str) -> JSONResponse:
    """Retrieve full dataset with all items (explicit, heavyweight).

    Use this when you need the actual data items.
    For just metadata, use GET /data/{id}

    Args:
        id: Dataset ID

    Returns:
        Full dataset with all items and metadata
    """
    storage = StorageManager()
    await storage.connect()

    try:
        dataset = await storage.retrieve(id)

        if not dataset:
            raise HTTPException(
                status_code=404,
                detail=f"Dataset '{id}' not found or expired (30-day retention)",
            )

        response = {
            "id": dataset.id,
            "schema": dataset.schema_name,
            "items": dataset.data.get("items", []),
            "metadata": {
                "seed": dataset.seed,
                "chaos_applied": dataset.chaos_applied or [],
                "created_at": dataset.created_at.isoformat(),
                "expires_at": dataset.expires_at.isoformat(),
            },
        }

        if dataset.metadata:
            response["metadata"].update(dataset.metadata)

        logger.info(
            "dataset_items_retrieved",
            id=id,
            schema=dataset.schema_name,
            count=len(response["items"]),
        )

        return JSONResponse(response)

    finally:
        await storage.close()


@router.delete("/data/{id}")
async def delete_dataset(id: str) -> JSONResponse:
    """Delete a persisted dataset.

    Removes from both Redis and PostgreSQL.

    Args:
        id: Dataset ID

    Returns:
        Success confirmation
    """
    storage = StorageManager()
    await storage.connect()

    try:
        deleted = await storage.delete(id)

        if not deleted:
            raise HTTPException(status_code=404, detail=f"Dataset '{id}' not found")

        logger.info("dataset_deleted", id=id)

        return JSONResponse({"deleted": True, "id": id})

    finally:
        await storage.close()
