"""Generate API routes.

Exposes ``POST /v1/generate`` to build a generator from a spec and emit values.
Behavior preserved; docstrings, types, and names follow the golden style.
"""
from __future__ import annotations

import random
import time
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, HTTPException

from faker_engine.api import build_generator, generate_many
from server.deps import get_settings, get_validator
from server.models import GenerateRequest, GenerateResponse

if TYPE_CHECKING:  # import only for typing to avoid cycles
    from faker_engine.types import JsonValue  # noqa: F401


router = APIRouter(prefix="/v1", tags=["generate"])

# TODO(removal): remove generate endpoint OR add selector endpoint to be saved as default
@router.post("/generate", response_model=GenerateResponse)
def generate(
    req: GenerateRequest,
    validator: Any = Depends(get_validator),
    settings: Any = Depends(get_settings),
) -> "JsonValue":
    """Produce values according to the generator configuration in ``req``.

    Args:
        req (GenerateRequest): Request payload containing the spec and options.
        validator (Any): Validator instance (duck-typed to our ``Validator`` API).
        settings (Any): Settings object providing feature flags (e.g., chaos).

    Returns:
        JsonValue: Mapping with generated ``items`` and ``count``.

    Raises:
        HTTPException: On validation failure (422) or injected chaos errors.
    """
    # Optional chaos injection (latency/errors), if enabled in settings.
    chaos = getattr(getattr(settings, "features", None), "chaos", None)
    if chaos and getattr(chaos, "enabled", False):
        # Latency injection
        lo, hi = getattr(chaos, "latency_ms_range", (0, 0))
        try:
            hi_int = int(hi)
            lo_int = int(lo)
        except Exception:
            hi_int = 0
            lo_int = 0
        if hi_int > 0:
            delay_ms = random.randint(max(0, lo_int), hi_int)
            time.sleep(delay_ms / 1000.0)

        # Error rate injection
        # TODO(validation): Validate chaos.error_rates types at startup and log rejects.
        for status_text, probability in getattr(chaos, "error_rates", {}).items():
            try:
                status_code = int(status_text)
                prob = float(probability)
            except Exception:
                continue  # ignore malformed entries to preserve behavior
            if prob > 0.0 and random.random() < prob:
                raise HTTPException(status_code=status_code, detail="chaos")

    # Validate the spec and return structured issues on failure.
    report = validator.validate(req.spec, raise_on_fail=False)
    if not getattr(report, "ok", False):
        issues = [
            {
                "code": issue.code,
                "path": list(issue.path) if getattr(issue, "path", None) else None,
                "msg": issue.msg,
                "detail": getattr(issue, "detail", None),
            }
            for issue in getattr(report, "issues", [])
        ]
        raise HTTPException(status_code=422, detail={"ok": False, "issues": issues})

    # Build the generator from the normalized spec (fallback to the raw spec) and emit values.
    gen = build_generator(getattr(report, "normalized", None) or req.spec)
    items = generate_many(gen, n=req.n, seed=req.seed, locale=req.locale)
    return {"items": items, "count": len(items)}
