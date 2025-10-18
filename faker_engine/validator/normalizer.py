from __future__ import annotations
from typing import Any


class SpecNormalizer:

    def __init__(self) -> None:
        try:
            from faker_engine import api as _api  # type: ignore
            self._builder = getattr(_api, "_builder",
                                    None)  # type: ignore[attr-defined]
            if self._builder is None:
                from faker_engine.spec_builder import \
                    SpecBuilder  # type: ignore
                self._builder = SpecBuilder()
        except Exception:  # pragma: no cover
            self._builder = None

    def normalize(self, spec: Any, path: str = "root") -> Any:
        b = self._builder
        fn = getattr(b, "_normalize", None) if b is not None else None
        if callable(fn):
            return fn(spec, path=path)
        return spec
