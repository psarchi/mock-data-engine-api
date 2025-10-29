from __future__ import annotations
from typing import Any, Dict, List
from mock_engine.chaos.types import ChaosOpPhase


def phase() -> str:
    return ChaosOpPhase.RESPONSE


def maybe_response(scope, ctx, payload: Any, schema_name: str | None, rng,
                   cfg: Dict[str, Any]) -> Any:
    if not cfg.get("enabled", False):
        return payload
    if not isinstance(payload, list) or len(payload) <= 1:
        return payload
    items = list(payload)
    rng.shuffle(items)
    return items
