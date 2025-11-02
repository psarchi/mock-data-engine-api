"""Schema-based generation routes.

Exposes ``GET /v1/schemas/{name}/generate`` which loads a stored schema file,
validates it, builds a generator, and returns generated items.

Notes:
    - Behavior preserved exactly; only docs/typing/TODOs and variable names were cleaned.
    - See TODO(BUG) notes where original logic is likely unintended but kept.
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import time
from pathlib import Path
from typing import Any, Optional

import yaml
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from faker_engine.api import build_generator
from faker_engine.chaos import ChaosManager, ChaosScope
from faker_engine.chaos.config import ChaosConfigView
from faker_engine.chaos.registry import build_ops_registry
from faker_engine.config import get_config_manager
from faker_engine.context import GenContext

from server.deps import get_settings, get_validator

router = APIRouter(prefix="/v1", tags=["schemas"])


def _schemas_dir() -> Path:
    """Return the base directory containing saved schemas.

    Returns:
        Path: Path to the schemas directory.

    Raises:
        HTTPException: If the directory does not exist.
    """
    env = os.getenv("SCHEMAS_DIR")
    base = Path(env) if env else Path(__file__).resolve().parents[2] / "schemas"
    if not base.exists():
        raise HTTPException(status_code=500, detail="Schemas directory not found")
    return base


def _load_schema_file(path: tuple[str, ...] | None) -> dict[str, Any]:
    """Load a schema file from disk.

    Args:
        path (tuple[str, ...] | None): **BUG:** annotated as tuple, but used as a :class:`Path`.
            Kept for compatibility with callers. The function expects a file path.

    Returns:
        dict[str, Any]: Parsed schema mapping (YAML/JSON).

    Raises:
        HTTPException: If the file is invalid or unsupported.
    """
    # TODO(BUG): Fix the parameter annotation to ``Path`` and update callers.
    try:
        with open(path, "r", encoding="utf-8") as f:  # type: ignore[arg-type]
            if Path(path).suffix in (".yaml", ".yml"):  # type: ignore[arg-type]
                return yaml.safe_load(f) or {}
            if Path(path).suffix == ".json":  # type: ignore[arg-type]
                return json.loads(f.read() or "{}")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid schema file: {exc}") from exc
    raise HTTPException(status_code=404, detail="Unsupported schema extension")


def _schema_path(name: str) -> Path:
    """Resolve a schema file path by name (tries .yaml/.yml/.json).

    Args:
        name (str): Canonical schema name without extension.

    Returns:
        Path: First matching path that exists.

    Raises:
        HTTPException: If no file is found.
    """
    base = _schemas_dir()
    for ext in (".yaml", ".yml", ".json"):
        candidate = base / f"{name}{ext}"
        if candidate.exists():
            return candidate
    raise HTTPException(status_code=404, detail=f"Schema '{name}' not found")


def _hash_spec_and_knobs(spec: dict[str, object], knobs: Optional[dict[str, Any]] = None) -> str:
    """Return a short fingerprint of ``spec`` + ``knobs`` for meta tagging.

    Args:
        spec (dict[str, object]): Normalized or raw specification mapping.
        knobs (dict[str, Any] | None): Scenario/knob values included in the hash.

    Returns:
        str: First 6 hex characters of SHA1(spec+knobs).
    """
    blob = json.dumps({"spec": spec, "knobs": knobs or {}}, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha1(blob).hexdigest()[:6]

# TODO: TOO much neets refractor and bug fixes.
@router.get("/schemas/{name}/generate")
def generate_schema(
    name: str,
    request: Request,
    n: int = Query(1, ge=1, le=1_000_000),
    seed: int | None = Query(None),
    locale: Optional[str] = Query(None),
    meta: bool = Query(True),
    scenario: Optional[str] = Query(None),
    validator: object = Depends(get_validator),
    settings: object = Depends(get_settings),
) -> object:
    """Generate records from a stored schema.

    Args:
        name (str): Canonical schema name (without extension).
        request (Request): Incoming request object.
        n (int): Number of records to generate (``1..1_000_000``).
        seed (int | None): Seed for deterministic behavior.
        locale (str | None): Faker locale for generation.
        meta (bool): If ``True``, attach ``__meta`` to each record when supported.
        scenario (str | None): Scenario name to include in meta/config hash.
        validator (object): Validator instance (duck-typed to our ``Validator`` API).
        settings (object): Settings object providing feature flags (e.g., chaos).

    Returns:
        object: FastAPI response payload or a pre-built response from chaos.

    Raises:
        HTTPException: On validation failure (422) or injected chaos errors.
    """
    path = _schema_path(name)
    spec = _load_schema_file(path)  # type: ignore[arg-type]

    report = validator.validate(spec, raise_on_fail=False)
    if not getattr(report, "ok", False):
        issues = [
            {
                "code": i.code,
                "path": list(i.path) if getattr(i, "path", None) else None,
                "msg": i.msg,
                "detail": getattr(i, "detail", None),
            }
            for i in getattr(report, "issues", [])
        ]
        raise HTTPException(status_code=422, detail={"ok": False, "issues": issues})

    normalized = getattr(report, "normalized", None) or spec
    gen = build_generator(normalized)

    e2e_start = time.perf_counter()
    chaos_info: dict[str, Any] = {
        "applied": False,
        "latency_ms": 0,
        "status_injected": None,
        "truncation": False,
    }

    # Settings-driven chaos (latency/errors); preserves original behavior.
    try:
        chaos_settings = getattr(getattr(settings, "features", None), "chaos", None)
        if chaos_settings and getattr(chaos_settings, "enabled", False):
            chaos_info["applied"] = True

            lo, hi = getattr(chaos_settings, "latency_ms_range", (0, 0))
            if isinstance(lo, (list, tuple)):
                lo, hi = lo
            if hi and int(hi) > 0:
                delay_ms = int(random.randint(int(lo), int(hi)))
                chaos_info["latency_ms"] = delay_ms
                time.sleep(delay_ms / 1000.0)

            # TODO(validation): Validate chaos.error_rates types at startup and log rejects.
            for code_text, prob in getattr(chaos_settings, "error_rates", {}).items():
                try:
                    status_code = int(code_text)
                    probability = float(prob)
                except Exception:
                    continue
                if probability > 0 and random.random() < probability:
                    chaos_info["status_injected"] = status_code
                    raise HTTPException(status_code=status_code, detail="chaos")
    except HTTPException:
        raise
    except Exception:
        # Preserve silent failure per original code.
        pass
    # TODO: next block is a mess; needs refactor
    ctx = GenContext(seed=seed, rng=random.Random(seed) if seed is not None else None, locale=locale)
    ctx.schema_name = name
    if isinstance(normalized, dict):
        ctx.schema_version = str(normalized.get("__version__", normalized.get("version", "unknown")))
    else:
        ctx.schema_version = "unknown"
    ctx.emit_meta = bool(meta) and bool(getattr(getattr(getattr(settings, "features", None), "generation_meta", None), "enabled", True))
    ctx.scenario = scenario
    ctx.config_hash = _hash_spec_and_knobs(normalized, {"scenario": scenario})
    cfg_map = settings.model_dump() if hasattr(settings,
                                               "model_dump") else dict(settings)
    cfg_view = ChaosConfigView(cfg_map)
    ops_cfg = getattr(cfg_view, "ops", {}) or {}
    ops_names = [name for name, spec in ops_cfg.items() if
                 (spec or {}).get("enabled", False)]
    ops_registry = build_ops_registry(ops_names)
    # chaos = ChaosManager(settings, ops_registry, ctx.rng)
    # early = chaos.apply_request("generate", ctx, request)
    early = None
    if early is not None:
        return early

    gen_start = time.perf_counter()
    items: list[dict[str, Any]] = []
    for _ in range(n):
        rec = gen.generate(ctx)
        if ctx.emit_meta and isinstance(rec, dict):
            rec["__meta"] = ctx.build_meta()
        items.append(rec)
    gen_ms = (time.perf_counter() - gen_start) * 1000.0
    e2e_ms = (time.perf_counter() - e2e_start) * 1000.0

    try:
        config_rev = get_config_manager().revision()
    except Exception:
        config_rev = None

    if bool(getattr(getattr(getattr(settings, "features", None), "generation_meta", None), "enabled", True)):
        for rec in items:
            if isinstance(rec, dict) and isinstance(rec.get("__meta"), dict):
                meta_patch: dict[str, Any] = {"config_rev": config_rev, "chaos": chaos}
                # TODO(BUG): Above injects the ChaosManager instance, not the ``chaos_info`` dict.
                #             Kept to preserve behavior; consider switching to ``chaos_info`` later.
                if bool(getattr(getattr(getattr(settings, "features", None), "generation_meta", None), "include_gen_ms", True)):
                    meta_patch["gen_ms"] = round(gen_ms, 3)
                if bool(getattr(getattr(getattr(settings, "features", None), "generation_meta", None), "include_e2e_ms", True)):
                    meta_patch["e2e_ms"] = round(e2e_ms, 3)
                rec["__meta"].update(meta_patch)

    # items = chaos.apply_response("generate", ctx, items, schema_name=name)
    #
    resp = JSONResponse(content={"schema": name, "count": len(items), "items": items})
    if ctx.seed is not None:
        resp.headers["X-Seed"] = str(ctx.seed)
    if ctx.request_id is not None:
        resp.headers["X-Request-Id"] = ctx.request_id
    return resp
