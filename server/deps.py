
"""Dependency providers for FastAPI routes (new schema pipeline)."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple

import yaml

from mock_engine import api as engine_api
from mock_engine.schema.builder import build_schema
from mock_engine.schema.registry import SchemaRegistry

_SCHEMAS_DIR = Path("schemas")
_GENERATOR_CACHE: Dict[str, Tuple[int, object]] = {}


def _load_schema_from_disk(name: str):
    """Load a schema document from disk and register it."""
    p = _SCHEMAS_DIR / f"{name}.yaml"
    if not p.exists():
        raise FileNotFoundError(f"schema file not found for '{name}': {p}")
    payload = yaml.safe_load(p.read_text(encoding="utf-8"))
    doc = build_schema(name, payload)
    SchemaRegistry.register(name, doc)
    return doc


def get_generator(name: str):
    """Return a generator built from the latest registered revision of ``name``."""
    try:
        doc = SchemaRegistry.get_latest_revision(name)
    except KeyError:
        doc = _load_schema_from_disk(name)
    latest_name = SchemaRegistry.get_latest_name(name)
    revision = SchemaRegistry.get_revision(latest_name)

    cached = _GENERATOR_CACHE.get(latest_name)
    if cached and cached[0] == revision:
        return cached[1]

    gen = engine_api.build(doc.contracts_by_path)
    _GENERATOR_CACHE[latest_name] = (revision, gen)
    return gen


def warmup_all(limit: int | None = None) -> int:
    count = 0
    for p in sorted(_SCHEMAS_DIR.glob("*.yml")) + sorted(_SCHEMAS_DIR.glob("*.yaml")):
        if limit and count >= limit:
            break
        name = p.stem
        try:
            _ = get_generator(name)
            count += 1
        except Exception:
            continue
    return count

def get_settings():
    from mock_engine.config import get_config_manager
    from mock_engine.config.access import ensure_config_fresh
    cm = get_config_manager()
    ensure_config_fresh(cm)
    return cm
