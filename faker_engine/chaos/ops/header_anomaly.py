from __future__ import annotations
from typing import Any, Dict, List
from faker_engine.chaos.types import ChaosOpPhase


def phase() -> str:
    return ChaosOpPhase.REQUEST


def maybe_request(scope, ctx, request, rng, cfg: Dict[str, Any]):
    if not cfg.get("enabled", False):
        return None
    patterns: List[str] = cfg.get("patterns",
                                  ["huge_value", "non_ascii", "dup_keys"])
    chosen = patterns[
        int(rng.random() * len(patterns))] if patterns else "huge_value"
    info = {"pattern": chosen}
    if chosen == "huge_value":
        info["header"] = "X-Debug-Blob"
        info["size"] = int(cfg.get("huge_value_bytes", 8192))
    elif chosen == "non_ascii":
        info["header"] = "X-NonAscii"
        info["value"] = "\uDC00\uD800"
    elif chosen == "dup_keys":
        info["header"] = "X-Dup-Key"
        info["count"] = int(cfg.get("dup_keys_count", 2))
    meta = getattr(ctx, "meta", None)
    if isinstance(meta, dict):
        meta.setdefault("chaos", {})
        meta["chaos"].setdefault("request_header_anomaly", info)
    return None
