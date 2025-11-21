"""Manual chaos exerciser for the schema generate endpoint.

Runs a baseline (no chaos), then forces each chaos op in turn and logs diffs.
Outputs are written to ``runner/log.log`` for manual inspection.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

try:
    from mock_engine.chaos.registry import get_registry
except Exception:
    get_registry = None  # type: ignore

BASE_URL = "http://127.0.0.1:8000"
SCHEMA_NAME = "ga4"
COUNT = 3
SEED = 123
RUNS_PER_OP = 2
DRIFT_RUNS_PER_OP = 5
# Default log path (falls back to stdout if not writable in this environment).
LOG_PATH = Path(__file__).parent / "log.log"


def fetch_generate(name: str, *, chaos_ops: str | None = None) -> Tuple[Dict[str, Any], int, Dict[str, str], float]:
    params = {"count": COUNT, "seed": SEED}
    if chaos_ops is not None:
        params["chaos_ops"] = chaos_ops
    query = urllib.parse.urlencode(params)
    url = f"{BASE_URL}/v1/schemas/{name}/generate?{query}"
    t0 = time.monotonic()
    with urllib.request.urlopen(url) as resp:  # noqa: S310 runtime-only helper
        raw = resp.read()
        status = getattr(resp, "status", 0)
        headers = {k.lower(): v for k, v in resp.headers.items()}
    elapsed = time.monotonic() - t0
    return json.loads(raw.decode("utf-8")), status, headers, elapsed


def collect_ops() -> List[str]:
    if callable(get_registry):
        try:
            return sorted(get_registry().keys())
        except Exception:
            pass
    # fallback static list (kept in sync manually if registry import fails)
    return [
        "duplicate_items",
        "encoding_corrupt",
        "partial_load",
        "truncate",
        "list_shuffle",
        "schema_bloat",
        "schema_field_nulling",
        "schema_time_skew",
        "time_skew",
        "random_header_case",
        "auth_fault",  # currently inert without middleware
        "http_error",
        "http_mismatch",
        "latency",
        # "rate_drift",  # not implemented
        "data_drift",
    ]


def diff(a: Any, b: Any, prefix: str = "") -> List[str]:
    paths: List[str] = []
    if type(a) != type(b):
        paths.append(f"{prefix or '<root>'}: type {type(a).__name__} -> {type(b).__name__}")
        return paths
    if isinstance(a, dict):
        keys = set(a) | set(b)
        for k in sorted(keys):
            sub = f"{prefix}.{k}" if prefix else str(k)
            if k not in a:
                paths.append(f"{sub}: <missing> -> {repr(b[k])[:200]}")
            elif k not in b:
                paths.append(f"{sub}: {repr(a[k])[:200]} -> <missing>")
            else:
                paths.extend(diff(a[k], b[k], sub))
        return paths
    if isinstance(a, list):
        if len(a) != len(b):  # type: ignore[arg-type]
            paths.append(f"{prefix or '<list>'}: len {len(a)} -> {len(b)}")
        for idx, (va, vb) in enumerate(zip(a, b)):  # type: ignore[arg-type]
            paths.extend(diff(va, vb, f"{prefix}[{idx}]"))
        return paths
    if a != b:
        paths.append(f"{prefix or '<root>'}: {repr(a)[:200]} -> {repr(b)[:200]}")
    return paths


def log_line(f, text: str) -> None:
    print(text, file=f)


def assess(op: str, base: dict, variant: dict, base_status: int, status: int, base_headers: Dict[str, str], headers: Dict[str, str], elapsed_ms: float) -> str:
    """Return a short verdict string for an op."""
    diffs = diff(base, variant)
    ignore_headers = {"date", "content-length", "server", "connection"}
    hdr_delta = []
    for k, v in headers.items():
        lk = k.lower()
        if lk in ignore_headers:
            continue
        if base_headers.get(lk) != v:
            hdr_delta.append(f"{lk}:{base_headers.get(lk)}->{v}")
    for k in base_headers:
        if k in ignore_headers:
            continue
        if k not in headers:
            hdr_delta.append(f"{k}:{base_headers.get(k)}-><missing>")
    obs = []
    if diffs:
        obs.append("payload changed")
    if status != base_status:
        obs.append(f"status {base_status}->{status}")
    if hdr_delta:
        obs.append("headers changed")
    if op == "latency" and elapsed_ms > 0:
        obs.append(f"latency {elapsed_ms:.2f}ms")
    if not obs:
        return "no change observed"
    return "; ".join(obs)


def main() -> int:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        fh = LOG_PATH.open("w", encoding="utf-8")
        dest = LOG_PATH
    except Exception:
        fh = sys.stdout
        dest = None

    with fh as f:
        log_line(f, f"# Chaos runner started {datetime.utcnow().isoformat()}Z")
        log_line(f, f"# base_url={BASE_URL} schema={SCHEMA_NAME} count={COUNT} seed={SEED}")

        log_line(f, "\n## baseline (no chaos)")
        baseline, base_status, base_headers, base_time = fetch_generate(SCHEMA_NAME, chaos_ops=None)
        log_line(f, f"status={base_status} latency_ms={base_time*1000:.2f}")
        log_line(f, f"headers={json.dumps(base_headers, ensure_ascii=False)}")
        log_line(f, json.dumps(baseline, ensure_ascii=False))

        ops = collect_ops()
        log_line(f, f"\n## ops ({len(ops)}): {', '.join(ops)}")
        for op in ops:
            log_line(f, f"\n### op: {op}")
            runs = DRIFT_RUNS_PER_OP if "drift" in op else RUNS_PER_OP
            for run in range(1, runs + 1):
                try:
                    variant, status, headers, elapsed = fetch_generate(SCHEMA_NAME, chaos_ops=op)
                except Exception as exc:  # noqa: BLE001
                    log_line(f, f"{op} run {run}: ERROR {exc}")
                    continue
                desc = variant.pop("chaos_descriptions", [])
                delta = diff(baseline, variant)
                verdict = assess(op, baseline, variant, base_status, status, base_headers, headers, elapsed * 1000)
                header_delta = []
                ignore_headers = {"date", "content-length", "server", "connection"}
                for k, v in headers.items():
                    lk = k.lower()
                    if lk in ignore_headers:
                        continue
                    if base_headers.get(lk) != v:
                        header_delta.append(f"{lk}: {base_headers.get(lk)} -> {v}")
                for k in base_headers:
                    if k in ignore_headers:
                        continue
                    if k not in headers:
                        header_delta.append(f"{k}: {base_headers.get(k)} -> <missing>")
                log_line(
                    f,
                    f"{op} run {run}: status={status} (+{status-base_status}) "
                    f"latency_ms={elapsed*1000:.2f} chaos={desc} changes={len(delta)} verdict={verdict}",
                )
                if header_delta:
                    for h in header_delta:
                        log_line(f, f"  hdr {h}")
                for d in delta[:50]:
                    log_line(f, f"  - {d}")
                if len(delta) > 50:
                    log_line(f, "  - ... truncated ...")
                time.sleep(0.05)

        log_line(f, "\n# done\n")
    if dest:
        print(f"Wrote log to {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
