from __future__ import annotations
from typing import Any
from pathlib import Path
import os
import yaml
from fastapi import APIRouter, HTTPException, Query, Depends
from server.deps import get_validator
from faker_engine.api import build_generator, generate_many

router = APIRouter(prefix="/v1", tags=["schemas"])


def _schemas_dir() -> Path:
    env = os.getenv("SCHEMAS_DIR")
    base = Path(env) if env else Path(__file__).resolve().parents[
                                     2] / "schemas"
    return base


@router.get("/schemas")
def list_schemas():
    base = _schemas_dir()
    if not base.exists():
        return {"schemas": []}
    names = sorted([p.stem for p in base.glob("*.yaml")] + [p.stem for p in
                                                            base.glob(
                                                                "*.yml")])
    return {"schemas": names}


@router.get("/schemas/{name}")
def get_schema(name: str):
    base = _schemas_dir()
    for ext in (".yaml", ".yml"):
        path = base / f"{name}{ext}"
        if path.exists():
            return {"name": name, "path": str(path)}
    raise HTTPException(status_code=404, detail=f"Schema '{name}' not found")


@router.get("/schemas/{name}/generate")
def generate_from_schema(
        name: str,
        n: int = Query(1, ge=1, le=10000),
        seed: int | None = None,
        locale: str = "en_US",
        validator=Depends(get_validator),
):
    base = _schemas_dir()
    spec_path: Path | None = None
    for ext in (".yaml", ".yml"):
        p = base / f"{name}{ext}"
        if p.exists():
            spec_path = p
            break
    if spec_path is None:
        raise HTTPException(status_code=404,
                            detail=f"Schema '{name}' not found")

    try:
        spec = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
        spec = spec.get("root", spec)
    except Exception as e:
        raise HTTPException(status_code=500,
                            detail=f"Failed to read YAML: {e}")

    report = validator.validate(spec, raise_on_fail=False, ignore_extras=False)
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

    gen = build_generator(report.normalized or spec)
    items = generate_many(gen, n=n, seed=seed, locale=locale)
    return {"schema": name, "count": len(items), "items": items}
