from __future__ import annotations
from typing import Any, Dict, List
from fastapi import Response
from faker_engine.chaos.types import ChaosOpPhase


def phase() -> str:
    return ChaosOpPhase.REQUEST


def maybe_request(scope, ctx, request, rng, cfg: Dict[str, Any]):
    if not cfg.get("enabled", False):
        return None
    modes: List[str] = cfg.get("modes", ["reject"])
    mode = modes[int(rng.random() * len(modes))] if modes else "reject"
    if mode == "reject":
        codes: List[int] = cfg.get("codes", [401, 403])
        code = int(codes[int(rng.random() * len(codes))]) if codes else 401
        headers = {
            "WWW-Authenticate": "Bearer realm=\"mock-data-engine\""} if code in (
        401, 403) else {}
        return Response(status_code=code, headers=headers, content=b"",
                        media_type="application/json")
    elif mode == "drop":
        setattr(ctx, "_chaos_auth", {"mode": "drop"})
        return None
    else:  # "invalid"
        setattr(ctx, "_chaos_auth", {"mode": "invalid"})
        return None
