from __future__ import annotations

from typing import Dict, Optional, Type

from mock_engine.chaos.ops.base import BaseChaosOp


class _Registry:
    def __init__(self) -> None:
        self._by_key: Dict[str, Type[BaseChaosOp]] = {}

    def register(self, cls: Type[BaseChaosOp]) -> None:
        if not isinstance(cls, type) or not issubclass(cls,
                                                       BaseChaosOp) or cls is BaseChaosOp:
            return
        key = getattr(cls, "key", None) or getattr(cls, "KEY",
                                                   None) or getattr(cls,
                                                                    "NAME",
                                                                    None)
        if not isinstance(key,
                          str) or not key.strip() or key.strip().lower() == "base":
            raise ValueError(
                f"Chaos op {cls.__name__} missing required 'key'.")
        key = key.strip()
        if key in self._by_key:
            raise ValueError(f"Duplicate chaos op key: {key}")
        # Contract check
        try:
            cls.validate_class()
        except Exception:
            BaseChaosOp.validate_class.__func__(
                cls)  # type: ignore[attr-defined]
        self._by_key[key] = cls

    def as_dict(self) -> Dict[str, Type[BaseChaosOp]]:
        return dict(self._by_key)

    def get_cls(self, key: str) -> Type[BaseChaosOp]:
        return self._by_key[key]


_registry_singleton: Optional[_Registry] = None


def _ensure_loaded() -> _Registry:
    global _registry_singleton
    if _registry_singleton is not None:
        return _registry_singleton

    reg = _Registry()
    from . import ops as ops_pkg  # noqa: F401
    for obj in vars(ops_pkg).values():
        if isinstance(obj, type) and issubclass(obj,
                                                BaseChaosOp) and obj is not BaseChaosOp:
            reg.register(obj)
    _registry_singleton = reg
    return reg


def get_registry() -> Dict[str, Type[BaseChaosOp]]:
    return _ensure_loaded().as_dict()


def require_op(name: str) -> Type[BaseChaosOp]:
    reg = _ensure_loaded()
    try:
        return reg.get_cls(name)
    except KeyError as e:
        raise KeyError(f"Unknown chaos op: {name!r}") from e
