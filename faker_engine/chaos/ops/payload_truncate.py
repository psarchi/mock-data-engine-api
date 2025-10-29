from __future__ import annotations
from typing import Any, Dict
from mock_engine.chaos.types import ChaosOpPhase


def phase() -> str:
    return ChaosOpPhase.RESPONSE


def maybe_response(scope, ctx, payload: Any, schema_name: str | None, rng,
                   cfg: Dict[str, Any]) -> Any:
    if not cfg.get("enabled", False):
        return payload
    if not isinstance(payload, list) or len(payload) == 0:
        return payload
    min_items = int(cfg.get("min_items", 1))
    if min_items < 0:
        min_items = 0
    n = len(payload)
    if n <= min_items:
        return payload
    keep = rng.randint(min_items, n)
    if keep >= n:
        return payload
    return payload[:keep]
