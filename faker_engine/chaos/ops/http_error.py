from __future__ import annotations
from typing import Any, Dict, List
from fastapi import Response
from mock_engine.chaos.types import ChaosOpPhase


def phase() -> str:
    return ChaosOpPhase.REQUEST


def maybe_request(scope, ctx, request, rng, cfg: Dict[str, Any]):
    if not cfg.get('enabled', False):
        return None
    codes: List[int] = cfg.get('codes', [500])
    if not codes:
        return None
    code = codes[int(rng.random() * len(codes))]
    return Response(status_code=int(code), content=b"",
                    media_type="application/json")
