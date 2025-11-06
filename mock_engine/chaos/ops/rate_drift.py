from __future__ import annotations
from typing import Any, Dict
from mock_engine.chaos.types import ChaosOpPhase
import math
import time


def phase() -> str:
    return ChaosOpPhase.REQUEST


def _sine(now_s: float, amp_ms: int, period_s: float) -> int:
    if period_s <= 0:
        return 0
    return int((math.sin(
        2 * math.pi * (now_s % period_s) / period_s) + 1.0) * 0.5 * amp_ms)


def _burst(rng, amp_ms: int, burst_prob: float) -> int:
    if burst_prob <= 0:
        return 0
    return int(amp_ms) if rng.random() < burst_prob else 0


def _random_walk(state: Dict[str, Any], rng, amp_ms: int, step_ms: int) -> int:
    cur = int(state.get("rw", 0))
    delta = rng.randint(-step_ms, step_ms)
    cur = max(0, min(amp_ms, cur + delta))
    state["rw"] = cur
    return cur


def maybe_request(scope, ctx, request, rng, cfg: Dict[str, Any]):
    if not cfg.get("enabled", False):
        return None
    pattern = str(cfg.get("pattern", "sine")).lower()
    amp_ms = int(cfg.get("amp_ms", 0))
    if amp_ms <= 0:
        return None

    now_s = time.time()
    add_ms = 0

    if pattern == "sine":
        period_s = float(cfg.get("period_s", 60.0))
        add_ms = _sine(now_s, amp_ms, period_s)
    elif pattern == "burst":
        burst_prob = float(cfg.get("burst_prob", 0.05))
        add_ms = _burst(rng, amp_ms, burst_prob)
    elif pattern == "random_walk":
        step_ms = int(cfg.get("step_ms", max(1, amp_ms // 10)))
        state = getattr(ctx, "_rate_drift_state", {})
        add_ms = _random_walk(state, rng, amp_ms, step_ms)
        setattr(ctx, "_rate_drift_state", state)
    else:
        period_s = int(cfg.get("period_s", 60))
        add_ms = amp_ms if int(now_s) % max(1, period_s) < (
                    period_s // 2) else 0

    if add_ms > 0:
        time.sleep(add_ms / 1000.0)
        return {"added_latency_ms": int(add_ms)}
    return None
