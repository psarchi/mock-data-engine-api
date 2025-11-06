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
    n = len(payload)
    cut_index = rng.randint(1, n)
    if cut_index >= n:
        return payload
    return payload[:cut_index]
