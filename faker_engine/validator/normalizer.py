from __future__ import annotations
from typing import Any
from faker_engine.spec_builder import SpecBuilder  # type: ignore
from faker_engine.core.registry import GeneratorRegistry  # type: ignore


class SpecNormalizer:

    def __init__(self) -> None:
        try:
            from faker_engine import api as _api  # type: ignore
        except Exception as e:  # pragma: no cover
            raise RuntimeError(
                "validator.normalizer: api module not available") from e

        builder = getattr(_api, "_builder", None)
        if not isinstance(builder, SpecBuilder):
            raise RuntimeError(
                "validator.normalizer: _builder must be SpecBuilder(registry)")
        if not isinstance(getattr(builder, "registry", None),
                          GeneratorRegistry):
            raise RuntimeError(
                "validator.normalizer: builder.registry must be GeneratorRegistry")
        self._builder = builder

    def normalize(self, spec: Any, path: str = "root") -> Any:
        fn = getattr(self._builder, "_normalize", None)
        if not callable(fn):
            raise RuntimeError(
                "validator.normalizer: SpecBuilder._normalize is not callable")
        return fn(spec, path=path)
