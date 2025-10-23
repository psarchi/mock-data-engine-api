from __future__ import annotations
from fastapi import APIRouter
from datetime import datetime, UTC

router = APIRouter(prefix="/v1", tags=["meta"])


@router.get("/health")
def health():
    return {"status": "ok", "ts": datetime.now(UTC).isoformat()}
