from __future__ import annotations
from typing import Any, Dict, List, Tuple, Union
from faker_engine.chaos.types import ChaosOpPhase


def phase() -> str:
    return ChaosOpPhase.RESPONSE


def _corrupt_string(s: str, rng) -> str:
    if not s:
        return s
    idx = rng.randint(0, len(s) - 1)
    ch = s[idx]
    replacement = "\uFFFD" if ch != "\uFFFD" else "*"
    return s[:idx] + replacement + s[idx + 1:]


def _walk_and_corrupt(obj: Any, rng, budget: int) -> Tuple[Any, int]:
    if budget <= 0:
        return obj, 0
    if isinstance(obj, dict):
        for k in list(obj.keys()):
            if budget <= 0:
                break
            v = obj[k]
            new_v, budget = _walk_and_corrupt(v, rng, budget)
            obj[k] = new_v
        return obj, budget
    if isinstance(obj, list):
        for i in range(len(obj)):
            if budget <= 0:
                break
            obj[i], budget = _walk_and_corrupt(obj[i], rng, budget)
        return obj, budget
    if isinstance(obj, str):
        return _corrupt_string(obj, rng), budget - 1
    return obj, budget


def maybe_response(scope, ctx, payload: Any, schema_name: str | None, rng,
                   cfg: Dict[str, Any]) -> Any:
    if not cfg.get("enabled", False):
        return payload
    if not isinstance(payload, list) or len(payload) == 0:
        return payload
    count = int(cfg.get("fields_to_corrupt", 1))
    if count <= 0:
        return payload
    items = list(payload)
    mutated = 0
    for i in range(len(items)):
        if mutated >= count:
            break
        items[i], remaining = _walk_and_corrupt(items[i], rng, count - mutated)
        mutated = count - remaining
    return items
