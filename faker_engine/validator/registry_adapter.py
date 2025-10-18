from __future__ import annotations
from typing import Mapping


class RegistryAdapter:

    def __init__(self) -> None:
        try:
            from faker_engine import api as _api  # type: ignore
            self._registry = getattr(_api,
                                     "_registry")  # type: ignore[attr-defined]
        except Exception:
            from faker_engine.core.registry import \
                GeneratorRegistry  # type: ignore
            import faker_engine.generators as gens  # type: ignore
            self._registry = GeneratorRegistry().register_from_module(gens)

    def get_class(self, gen_name: str):
        return self._registry.get_cls(gen_name)

    def get_aliases(self, gen_name: str) -> Mapping[str, str]:
        cls = self.get_class(gen_name)
        meta = getattr(cls, "__meta__", {}) or {}
        aliases = meta.get("aliases", {}) or {}
        return {str(k): str(v) for k, v in aliases.items()}
