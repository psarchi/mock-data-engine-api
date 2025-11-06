from __future__ import annotations
from typing import Any, Dict, List, Iterable
from mock_engine.chaos.types import ChaosOpPhase


def phase() -> str:
    return ChaosOpPhase.RESPONSE


def _iter_fields(item: dict, fields: List[str]) -> Iterable[str]:
    for f in fields:
        if f in item:
            yield f


def maybe_response(scope, ctx, payload: Any, schema_name: str | None, rng,
                   cfg: Dict[str, Any]) -> Any:
    if not cfg.get("enabled", False):
        return payload
    if not isinstance(payload, list):
        return payload

    max_skew_s = int(cfg.get("max_skew_s", 0))
    if max_skew_s <= 0:
        return payload
    direction = str(cfg.get("direction", "both")).lower()
    fields = cfg.get("fields", []) or []

    out: List[Any] = []
    for item in payload:
        if not isinstance(item, dict):
            out.append(item)
            continue
        new_item = dict(item)
        if not fields:
            out.append(new_item)
            continue

        skew = rng.randint(1, max_skew_s)
        if direction == "past":
            skew = -abs(skew)
        elif direction == "future":
            skew = abs(skew)
        else:
            skew = (-skew) if rng.random() < 0.5 else skew

        for key in _iter_fields(new_item, fields):
            val = new_item.get(key)
            if isinstance(val, (int, float)):
                new_item[key] = val + skew
        out.append(new_item)
    return out
