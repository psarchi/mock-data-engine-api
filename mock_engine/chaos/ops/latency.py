from __future__ import annotations
import time
from typing import Any, Dict
from mock_engine.chaos.types import ChaosOpPhase

def phase() -> str:
    return ChaosOpPhase.REQUEST

def maybe_request(scope, ctx, request, rng, cfg: Dict[str, Any]):
    if not cfg.get('enabled', False):
        return None
    min_ms = int(cfg.get('min_ms', 0))
    max_ms = int(cfg.get('max_ms', 0))
    if max_ms <= 0 or max_ms < min_ms:
        return None
    delay_ms = int(min_ms + (max_ms - min_ms) * rng.random())
    if delay_ms > 0:
        time.sleep(delay_ms / 1000.0)
        return {'added_latency_ms': delay_ms}
    return None
