"""Registry adapter for validator components.

Resolves the framework's global :class:`~mock_engine.core.registry.GeneratorRegistry`
from ``mock_engine.api`` and provides thin helpers to look up generator
classes, aliases, and resolve a generator by name.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from mock_engine.core.registry import GeneratorRegistry
from mock_engine.generators.base import BaseGenerator

if TYPE_CHECKING:  # import only for typing to avoid cycles
    from typing import Mapping as _MappingAlias  # noqa: F401


class RegistryAdapter:
    """Adapter around :class:`GeneratorRegistry` for validator use.

    Raises:
        RuntimeError: If the global registry cannot be resolved or has an unexpected type.
    """

    __slots__ = ("_registry",)

    def __init__(self) -> None:
        """Initialize by resolving the global registry from ``mock_engine.api``.

        Returns:
            None: Constructor performs resolution/validation only.
        """
        try:
            from mock_engine import api as _api
        except Exception as exc:  # noqa: BLE001 (preserve behavior)
            raise RuntimeError("validator.registry_adapter: api module not available") from exc
        registry = getattr(_api, "_registry", None)
        if not isinstance(registry, GeneratorRegistry):
            raise RuntimeError("validator.registry_adapter: _registry must be GeneratorRegistry")
        self._registry: GeneratorRegistry = registry

    def get_class(self, generator_name: str) -> type[BaseGenerator]:
        """Return the generator class registered under ``generator_name``.

        Args:
            generator_name (str): Canonical or alias generator name.

        Returns:
            type[BaseGenerator]: Registered generator class.
        """
        return self._registry.get_cls(generator_name)

    def get_aliases(self, generator_name: str) -> Mapping[str, str]:
        """Return alias mapping for a generator's metadata.

        Args:
            generator_name (str): Canonical or alias generator name.

        Returns:
            Mapping[str, str]: Mapping from alias to canonical field name.
        """
        cls = self.get_class(generator_name)
        meta = getattr(cls, "__meta__", {}) or {}
        aliases = meta.get("aliases", {}) or {}
        return {str(key): str(value) for key, value in aliases.items()}

    def resolve(self, generator_name: str) -> BaseGenerator | tuple[type[BaseGenerator], str]:
        """Resolve a generator by alias or canonical name.

        Uses ``GeneratorRegistry.resolve`` when available. If the registry does
        not expose ``resolve``, falls back to returning ``(cls, canonical_name)``
        for the caller to instantiate.

        Args:
            generator_name (str): Canonical or alias generator name.

        Returns:
            BaseGenerator | tuple[type[BaseGenerator], str]: Resolved generator instance
                or a tuple of ``(class, canonical_name)`` when the registry lacks a
                resolver.

        Raises:
            RuntimeError: If the class cannot be located (propagated from registry).
        """
        reg = self._registry
        if hasattr(reg, "resolve") and callable(getattr(reg, "resolve")):
            return reg.resolve(generator_name)  # type: ignore[return-value]
        cls = reg.get_cls(generator_name)
        canonical = getattr(cls, "__name__", "generator").lower()
        # TODO(compat): Replace tuple fallback with an instance once all call sites expect objects.
        return (cls, canonical)
