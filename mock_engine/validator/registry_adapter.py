"""Registry adapter for validator components.

Provides thin helpers to look up generator classes, aliases, and resolve
generators by name using the unified Registry.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from mock_engine.registry import Registry
from mock_engine.generators.base import BaseGenerator

if TYPE_CHECKING:  # import only for typing to avoid cycles
    from typing import Mapping as _MappingAlias  # noqa: F401


class RegistryAdapter:
    """Adapter around unified Registry for validator use."""

    __slots__ = ()

    def __init__(self) -> None:
        """Initialize the adapter.

        Note: Uses the unified Registry directly - generators auto-register on import.
        """
        # Ensure generators are loaded
        import mock_engine.generators  # noqa: F401

    def get_class(self, generator_name: str) -> type[BaseGenerator]:
        """Return the generator class registered under ``generator_name``.

        Args:
            generator_name (str): Generator key (e.g., "timestamp", "int", "string").

        Returns:
            type[BaseGenerator]: Registered generator class.

        Raises:
            KeyError: If no generator is registered for ``generator_name``.
        """
        cls = Registry.get(BaseGenerator, generator_name)
        if cls is None:
            available = list(Registry.get_all(BaseGenerator).keys())
            raise KeyError(
                f"unknown generator '{generator_name}'. available: {', '.join(sorted(available))}"
            )
        return cls

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

    def resolve(self, generator_name: str) -> tuple[type[BaseGenerator], str]:
        """Resolve a generator by name.

        Returns a tuple of (class, canonical_name) for the caller to instantiate.

        Args:
            generator_name (str): Generator key (e.g., "timestamp", "int", "string").

        Returns:
            tuple[type[BaseGenerator], str]: Tuple of (class, canonical_name).

        Raises:
            KeyError: If the class cannot be located.
        """
        cls = self.get_class(generator_name)
        canonical = getattr(cls, "__name__", "generator").lower()
        return (cls, canonical)
