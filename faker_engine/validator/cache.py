from __future__ import annotations
from typing import Any, Dict
from pydantic import BaseModel

# Simple in-memory cache for spec->model
_MODEL_CACHE: Dict[str, type[BaseModel]] = {}


def get_cached(name: str) -> type[BaseModel] | None:
    return _MODEL_CACHE.get(name)


def set_cached(name: str, model: type[BaseModel]) -> None:
    _MODEL_CACHE[name] = model
