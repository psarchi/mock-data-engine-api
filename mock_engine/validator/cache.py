"""Validator model cache.

Holds a simple in-memory mapping from canonical names to Pydantic model types.
Thread safety and eviction are intentionally out of scope here.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel

__all__ = ["get_cached", "set_cached"]

# TODO(concurrency): Guard with a lock if validators are built from multiple threads.
# TODO(eviction): Consider a size limit or LRU policy if the model set can grow unbounded.
_MODEL_CACHE: dict[str, type[BaseModel]] = {}


def get_cached(name: str) -> type[BaseModel] | None:
    """Return a cached Pydantic model class by canonical name.

    Args:
        name (str): Canonical generator/model name.

    Returns:
        type[BaseModel] | None: Cached model class if present, otherwise ``None``.
    """
    return _MODEL_CACHE.get(name)


def set_cached(name: str, model: type[BaseModel]) -> None:
    """Store a Pydantic model class under a canonical name.

    Args:
        name (str): Canonical name.
        model (type[BaseModel]): Pydantic model class to cache.

    Returns:
        None: This function updates internal state for its side-effect.
    """
    _MODEL_CACHE[name] = model
