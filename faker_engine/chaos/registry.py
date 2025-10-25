from __future__ import annotations
from importlib import import_module
from typing import Dict, Any, Iterable


def build_ops_registry(names: Iterable[str]) -> Dict[str, Any]:
    registry: Dict[str, Any] = {}
    for name in names:
        try:
            mod = import_module(f"faker_engine.chaos.ops.{name}")
            registry[name] = mod
        except Exception:
            continue
    return registry
