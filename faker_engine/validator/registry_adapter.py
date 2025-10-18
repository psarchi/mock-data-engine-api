from __future__ import annotations
from typing import Mapping
from faker_engine.core.registry import GeneratorRegistry  # type: ignore


class RegistryAdapter:

    def __init__(self) -> None:
        try:
            from faker_engine import api as _api  # type: ignore
            registry = getattr(_api, "_registry")
        except Exception as e:
            raise RuntimeError(
                "validator.registry_adapter: api._registry is required") from e
        if not isinstance(registry, GeneratorRegistry):
            raise RuntimeError(
                "validator.registry_adapter: _registry must be GeneratorRegistry")
        self._registry = registry

    def get_class(self, gen_name: str):
        return self._registry.get_cls(gen_name)

    def get_aliases(self, gen_name: str) -> Mapping[str, str]:
        cls = self.get_class(gen_name)
        meta = getattr(cls, "__meta__", {}) or {}
        aliases = meta.get("aliases", {}) or {}
        return {str(k): str(v) for k, v in aliases.items()}

    def resolve(self, gen_name: str):
        reg = self._registry
        if hasattr(reg, "resolve"):
            return reg.resolve(gen_name)
        cls = reg.get_cls(gen_name)
        return cls, cls.__name__.lower()
