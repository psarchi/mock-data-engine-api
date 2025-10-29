"""Utility helpers for generator classes.

This module intentionally keeps behavior minimal and side-effect free.
"""
from __future__ import annotations

import inspect
from random import Random
from typing import TYPE_CHECKING, Any, Type, Sequence

if TYPE_CHECKING:  # import only for typing to avoid cycles
    from mock_engine.types import JsonValue  # noqa: F401


# TODO (core): Wire all utils here for generators.

def get_init_fields(cls: Type[object]) -> list[str]:
    """Return constructor field names for a generator class.

    Args:
        cls (Type[object]): Class to introspect (its ``__init__`` is inspected).

    Returns:
        list[str]: Field names derived from the ``__init__`` signature (excluding ``self``).
    """
    fields = getattr(cls, "_cached_init_fields", None)
    if fields is not None:
        return fields
    sig = inspect.signature(cls.__init__)
    fields = [param.name for param in sig.parameters.values() if param.name != "self"]
    setattr(cls, "_cached_init_fields", fields)
    return fields


def _pick_index(cls: object, rng: Random) -> int:
    """Pick an index into ``cls.values`` with optional weighting.

    ``cls`` is expected to expose ``values`` (``Sequence[Any]``) and optional
    ``weights`` (``Sequence[float] | None``). When ``weights`` is falsy, a uniform
    selection is performed; otherwise, a linear scan on cumulative weights is used.

    Args:
        cls (object): Holder of ``values`` and optional ``weights`` attributes.
        rng (Random): Deterministic random generator.

    Returns:
        int: Index selected in ``[0, len(cls.values) - 1]``.

    Raises:
        ValueError: If ``cls.values`` is empty.
    """
    values: Sequence[Any] = getattr(cls, "values")
    if not values:
        # TODO(errors): Consider a domain-specific error (e.g., MissingChildError) at call sites.
        raise ValueError("values must be a non-empty sequence")

    weights: Sequence[float] | None = getattr(cls, "weights", None)
    if not weights:
        return rng.randint(0, len(values) - 1)

    # TODO(validation): Ensure length(weights) == length(values) and all weights are non-negative/finite.
    # TODO(perf): Precompute cumulative weights once and reuse.
    total = float(sum(weights))
    r = rng.random() * total
    acc = 0.0
    for index, weight in enumerate(weights):
        acc += float(weight)
        if r <= acc:
            return index
    return len(values) - 1
