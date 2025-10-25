from __future__ import annotations
from typing import Any, Optional, Mapping
from pathlib import Path
import os
import json
import hashlib
import random
import time
import yaml
from fastapi import APIRouter, HTTPException, Query, Depends, Request
from fastapi.responses import JSONResponse
from server.deps import get_validator, get_settings
from faker_engine.chaos import ChaosManager, ChaosScope
from faker_engine.api import build_generator  # reuse your existing builder
from faker_engine.config import get_config_manager
from faker_engine.context import GenContext

router = APIRouter(prefix="/v1", tags=["schemas"])


def _schemas_dir() -> Path:
    env = os.getenv("SCHEMAS_DIR")
    base = Path(env) if env else Path(__file__).resolve().parents[
                                     2] / "schemas"
    if not base.exists():
        raise HTTPException(status_code=500,
                            detail="Schemas directory not found")
    return base


def _load_schema_file(path: Path) -> Mapping[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            if path.suffix in (".yaml", ".yml"):
                return yaml.safe_load(f) or {}
            elif path.suffix == ".json":
                return json.loads(f.read() or "{}")
    except Exception as e:
        raise HTTPException(status_code=400,
                            detail=f"Invalid schema file: {e}")
    raise HTTPException(status_code=404, detail="Unsupported schema extension")


def _schema_path(name: str) -> Path:
    base = _schemas_dir()
    for ext in (".yaml", ".yml", ".json"):
        p = base / f"{name}{ext}"
        if p.exists():
            return p
    raise HTTPException(status_code=404, detail=f"Schema '{name}' not found")


def _hash_spec_and_knobs(spec: Mapping[str, Any],
                         knobs: Optional[Mapping[str, Any]] = None) -> str:
    blob = json.dumps({"spec": spec, "knobs": knobs or {}}, sort_keys=True,
                      default=str).encode("utf-8")
    return hashlib.sha1(blob).hexdigest()[:6]


@router.get("/schemas/{name}/generate")
def generate_schema(
        name: str,
        request: Request,
        n: int = Query(1, ge=1, le=1_000_000),
        seed: Optional[int] = Query(None),
        locale: Optional[str] = Query(None),
        meta: bool = Query(True),
        scenario: Optional[str] = Query(None),
        validator=Depends(get_validator),
        settings=Depends(get_settings),
):
    path = _schema_path(name)
    spec = _load_schema_file(path)
    report = validator.validate(spec, raise_on_fail=False)
    if not report.ok:
        raise HTTPException(status_code=422, detail={
            "ok": False,
            "issues": [{
                "code": i.code,
                "path": list(i.path) if getattr(i, "path", None) else None,
                "msg": i.msg,
                "detail": getattr(i, "detail", None)} for i in report.issues]
        })

    normalized = report.normalized or spec
    gen = build_generator(normalized)

    # timing + chaos
    e2e_start = time.perf_counter()
    chaos = {"applied": False, "latency_ms": 0, "status_injected": None,
             "truncation": False}
    try:
        c = getattr(settings.features, "chaos", None)
        if c and getattr(c, "enabled", False):
            chaos["applied"] = True
            lo, hi = getattr(c, "latency_ms_range", (0, 0))
            if isinstance(lo, (
                    list, tuple)):  # support tuple form from other endpoint
                lo, hi = lo
            if hi and int(hi) > 0:
                delay_ms = int(random.randint(int(lo), int(hi)))
                chaos["latency_ms"] = delay_ms
                time.sleep(delay_ms / 1000.0)
            # status injection
            for code_str, prob in getattr(c, "error_rates", {}).items():
                try:
                    code = int(code_str)
                    p = float(prob)
                except Exception:
                    continue
                if p > 0 and random.random() < p:
                    chaos["status_injected"] = code
                    raise HTTPException(status_code=code, detail="chaos")
    except HTTPException:
        raise
    except Exception:
        pass

    ctx = GenContext(seed=seed,
                     rng=random.Random(seed) if seed is not None else None,
                     locale=locale)
    ctx.schema_name = name
    if isinstance(normalized, dict):
        ctx.schema_version = str(normalized.get("__version__",
                                                normalized.get("version",
                                                               "unknown")))
    else:
        ctx.schema_version = "unknown"
    ctx.emit_meta = bool(meta) and bool(
        getattr(getattr(settings.features, 'generation_meta'), 'enabled',
                True))
    ctx.scenario = scenario
    ctx.config_hash = _hash_spec_and_knobs(normalized, {"scenario": scenario})
    chaos = ChaosManager(settings)
    early = chaos.apply_request("generate", ctx, request)
    if early is not None:
        return early

    # generation & meta timing
    gen_start = time.perf_counter()
    items = []
    for _ in range(n):
        rec = gen.generate(ctx)
        if ctx.emit_meta:
            rec["__meta"] = ctx.build_meta()
        items.append(rec)

    # timings and config revision
    gen_ms = (time.perf_counter() - gen_start) * 1000.0
    e2e_ms = (time.perf_counter() - e2e_start) * 1000.0
    try:
        config_rev = get_config_manager().revision()
    except Exception:
        config_rev = None
    if bool(getattr(getattr(settings.features, 'generation_meta'), 'enabled',
                    True)):
        for rec in items:
            if isinstance(rec, dict) and isinstance(rec.get("__meta"), dict):
                _tmp = {"config_rev": config_rev, "chaos": chaos}
                if bool(getattr(getattr(settings.features, "generation_meta"),
                                "include_gen_ms", True)):
                    _tmp["gen_ms"] = round(gen_ms, 3)
                if bool(getattr(getattr(settings.features, "generation_meta"),
                                "include_e2e_ms", True)):
                    _tmp["e2e_ms"] = round(e2e_ms, 3)
                rec["__meta"].update(_tmp)
    items = chaos.apply_response("generate", ctx, items, schema_name=name)

    resp = JSONResponse(
        content={"schema": name, "count": len(items), "items": items})
    if ctx.seed is not None:
        resp.headers["X-Seed"] = str(ctx.seed)
    if ctx.request_id is not None:
        resp.headers["X-Request-Id"] = ctx.request_id
    return resp
