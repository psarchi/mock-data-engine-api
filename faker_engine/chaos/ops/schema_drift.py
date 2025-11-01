from __future__ import annotations
from typing import Any, Dict, List
from faker_engine.chaos.types import ChaosOpPhase


def phase() -> str:
    return ChaosOpPhase.RESPONSE


def maybe_response(scope, ctx, payload: Any, schema_name: str | None, rng,
                   cfg: Dict[str, Any]) -> Any:
    if not cfg.get("enabled", False):
        return payload
    if not isinstance(payload, list):
        return payload

    add_fields: Dict[str, Any] = cfg.get("add_fields", {}) or {}
    drop_fields: List[str] = list(cfg.get("drop_fields", []) or [])
    rename_fields: Dict[str, str] = cfg.get("rename_fields", {}) or {}

    out: List[Any] = []
    for item in payload:
        if not isinstance(item, dict):
            out.append(item)
            continue
        cur = {}
        for k, v in item.items():
            new_k = rename_fields.get(k, k)
            cur[new_k] = v
        for k in drop_fields:
            if k in cur:
                del cur[k]
        for k, v in add_fields.items():
            if k not in cur:
                cur[k] = v
        out.append(cur)
    return out
