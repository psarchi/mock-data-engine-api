from __future__ import annotations
from typing import Any, Dict, List
from faker_engine.chaos.types import ChaosOpPhase


def phase() -> str:
    return ChaosOpPhase.RESPONSE


def _choose_weighted(rng, items: List[str], weights: List[float]) -> str:
    total = sum(w for w in weights if w > 0)
    if total <= 0:
        return items[int(rng.random() * len(items))]
    pick = rng.random() * total
    acc = 0.0
    for it, w in zip(items, weights):
        if w <= 0:
            continue
        acc += w
        if pick <= acc:
            return it
    return items[-1]


def maybe_response(scope, ctx, payload: Any, schema_name: str | None, rng,
                   cfg: Dict[str, Any]) -> Any:
    if not cfg.get("enabled", False):
        return payload
    if not isinstance(payload, list):
        return payload

    fields_cfg: Dict[str, Dict[str, Any]] = cfg.get("fields", {}) or {}
    if not fields_cfg:
        return payload

    q_global = float(cfg.get("q", 0.15))

    out: List[Any] = []
    for item in payload:
        if not isinstance(item, dict):
            out.append(item);
            continue
        new_item = dict(item)
        for fname, fcfg in fields_cfg.items():
            if fname not in new_item:
                continue
            if rng.random() >= float(fcfg.get("q", q_global)):
                continue
            mode = str(fcfg.get("mode", "categorical")).lower()
            if mode == "categorical":
                choices = list(fcfg.get("choices", []))
                if not choices:
                    # if no explicit choices, fallback to keep original or skip
                    continue
                base_w = [1.0] * len(choices)
                delta = fcfg.get("weights_delta", {}) or {}
                weights = [
                    max(0.0, base_w[i] + float(delta.get(choices[i], 0.0))) for
                    i in range(len(choices))]
                new_item[fname] = _choose_weighted(rng, choices, weights)
            else:  # numeric
                val = new_item.get(fname)
                if isinstance(val, (int, float)):
                    add = float(fcfg.get("add", 0.0))
                    mul = float(fcfg.get("mul", 1.0))
                    jitter = float(fcfg.get("jitter", 0.0))
                    jitter_val = (rng.random() * 2.0 - 1.0) * jitter
                    new_val = (val * mul) + add + jitter_val
                    new_item[fname] = int(round(new_val)) if isinstance(val,
                                                                        int) else new_val
        out.append(new_item)
    return out
