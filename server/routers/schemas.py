from __future__ import annotations
from typing import Any, Optional, Mapping
from pathlib import Path
import os
import json
import hashlib
import random
import yaml
from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import JSONResponse
from server.deps import get_validator
from faker_engine.api import build_generator
from faker_engine.context import GenContext

router = APIRouter(prefix="/v1", tags=["schemas"])


def _schemas_dir() -> Path:
    env = os.getenv("SCHEMAS_DIR")
    base = Path(env) if env else Path(__file__).resolve().parents[2] / "schemas"
    if not base.exists():
        raise HTTPException(status_code=500, detail="Schemas directory not found")
    return base


def _load_schema_file(path: Path) -> Mapping[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            if path.suffix in (".yaml", ".yml"):
                return yaml.safe_load(f) or {}
            elif path.suffix == ".json":
                return json.loads(f.read() or "{}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid schema file: {e}")
    raise HTTPException(status_code=404, detail="Unsupported schema extension")


def _schema_path(name: str) -> Path:
    base = _schemas_dir()
    for ext in (".yaml", ".yml", ".json"):
        p = base / f"{name}{ext}"
        if p.exists():
            return p
    raise HTTPException(status_code=404, detail=f"Schema '{name}' not found")


def _hash_spec_and_knobs(spec: Mapping[str, Any], knobs: Optional[Mapping[str, Any]] = None) -> str:
    blob = json.dumps({"spec": spec, "knobs": knobs or {}}, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha1(blob).hexdigest()[:6]


@router.get("/schemas/{name}/generate")
def generate_schema(
    name: str,
    n: int = Query(1, ge=1, le=1_000_000),
    seed: Optional[int] = Query(None),
    locale: Optional[str] = Query(None),
    meta: bool = Query(True),
    scenario: Optional[str] = Query(None),
    validator = Depends(get_validator),
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
                "detail": getattr(i, "detail", None),
            } for i in report.issues]
        })

    normalized = report.normalized or spec
    gen = build_generator(normalized)

    ctx = GenContext(seed=seed, rng=random.Random(seed) if seed is not None else None, locale=locale)
    ctx.schema_name = name
    if isinstance(normalized, dict):
        ctx.schema_version = str(normalized.get("__version__", normalized.get("version", "unknown")))
    else:
        ctx.schema_version = "unknown"
    ctx.emit_meta = bool(meta)
    ctx.scenario = scenario
    ctx.config_hash = _hash_spec_and_knobs(normalized, {"scenario": scenario})

    # meta
    items = []
    for _ in range(n):
        rec = gen.generate(ctx)
        if ctx.emit_meta:
            rec["__meta"] = ctx.build_meta()
        items.append(rec)

    resp = JSONResponse(content={"schema": name, "count": len(items), "items": items})
    if ctx.seed is not None:
        resp.headers["X-Seed"] = str(ctx.seed)
    if ctx.request_id is not None:
        resp.headers["X-Request-Id"] = ctx.request_id
    return resp
