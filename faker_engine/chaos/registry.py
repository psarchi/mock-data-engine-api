from __future__ import annotations

from collections.abc import Iterable
from importlib import import_module
from typing import Any

__all__ = ["build_ops_registry"]


# TODO(validation): Verify that each imported module exposes the expected API
#                   (e.g., phase(), maybe_request(...), maybe_response(...)).
# TODO(errors): Consider logging import failures for visibility in non-dev envs.
# TODO: introduce caching for registered ops maybe register everything at once and cache?

def build_ops_registry(names: Iterable[str]) -> dict[str, Any]:
    """Build a registry mapping op names to imported modules.

    Args:
        names (Iterable[str]): Operation module names to import from
            ``faker_engine.chaos.ops``.

    Returns:
        dict[str, Any]: Mapping ``name → module`` for successfully imported ops.
    """
    registry: dict[str, Any] = {}
    for op_name in names:
        try:
            module = import_module(f"faker_engine.chaos.ops.{op_name}")
        except Exception:  # noqa: BLE001 (preserved behavior)
            # Keep silent failure for compatibility.
            continue
        registry[str(op_name)] = module
    return registry
