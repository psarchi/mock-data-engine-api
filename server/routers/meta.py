
from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter

router = APIRouter(prefix="/v1", tags=["meta"])


@router.get("/health")
def health() -> dict[str, str]:
    """Return liveness status and an ISO-8601 UTC timestamp.

    Returns:
        dict[str, str]: Mapping with keys:
            - ``status``: Always ``"ok"`` when the service is alive.
            - ``ts``: Current time in ISO-8601 with ``Z`` (UTC) designator.
    """
    # TODO(observability): Attach build/version/commit metadata when available.
    return {"status": "ok", "ts": datetime.now(UTC).isoformat()}
