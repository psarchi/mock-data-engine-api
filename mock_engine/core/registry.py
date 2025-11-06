"""Registry that maps generator aliases to concrete classes.

Provides utilities to register generators, resolve classes by alias or canonical
name, and introspect the available set for documentation or UIs.
"""
from __future__ import annotations

from types import ModuleType
from typing import TYPE_CHECKING, Any, Iterable

from mock_engine.core.errors import DuplicateAliasError

if TYPE_CHECKING:  # avoid import cycle at runtime
    from mock_engine.generators.base import BaseGenerator


# TODO(arch): consider adding caching of registered classes.
class GeneratorRegistry:
    """Registry that maps generator aliases to concrete classes.

    Provides utilities to register generators, resolve classes by alias or canonical
    name, and introspect the available set for documentation or UIs.
    """
    def __init__(self, initial: dict[str, type["BaseGenerator"]] | None = None) -> None:
        """Initialize the registry.

        Args:
            initial (dict[str, type[BaseGenerator]] | None): Optional initial
                alias map. Keys are normalized alias strings, values are
                generator classes.
        """
        self._catalog: dict[str, type["BaseGenerator"]] = dict(initial or {})

    def _normalize(self, name: str) -> str:
        """Normalize an alias/canonical name for lookup consistency."""
        return name.strip().lower().replace(" ", "_")

    def register(self, cls: type["BaseGenerator"], *aliases: str) -> "GeneratorRegistry":
        """Register a generator class under its canonical and alias names.

        Canonical name is ``cls.__name__.lower()``; aliases are taken from the
        class attribute ``__aliases__`` (if present) and any explicit
        ``*aliases`` provided to this method.

        Args:
            cls (type[BaseGenerator]): Generator class to register.
            *aliases (str): Additional alias strings.

        Returns:
            GeneratorRegistry: ``self`` to allow chaining.

        Raises:
            DuplicateAliasError: An alias is already registered to a different class.
            # TODO(errors): raise InvalidRegistrationError if ``cls`` lacks required API
        """
        names: set[str] = {self._normalize(cls.__name__)}
        for alias in getattr(cls, "__aliases__", ()):
            if isinstance(alias, str) and alias:
                names.add(self._normalize(alias))
        for alias in aliases:
            if isinstance(alias, str) and alias:
                names.add(self._normalize(alias))

        for name in names:
            if name in self._catalog and self._catalog[name] is not cls:
                raise DuplicateAliasError(f"duplicate generator alias: {name}")
            self._catalog[name] = cls
        return self

    def register_many(self, pairs: Iterable[Any]) -> "GeneratorRegistry":
        """Register many generators from an iterable.

        Each item can be either a generator class, or a tuple of
        ``(class, *aliases)``.

        Args:
            pairs (Iterable[Any]): Items to register.

        Returns:
            GeneratorRegistry: ``self`` for chaining.
        """
        for item in pairs:
            if isinstance(item, tuple) and item and isinstance(item[0], type):
                cls = item[0]
                extra_aliases = tuple(str(a) for a in item[1:])
                self.register(cls, *extra_aliases)
            elif isinstance(item, type):
                self.register(item)
        return self

    def register_from_module(self, module: ModuleType) -> "GeneratorRegistry":
        """Register all generator classes exported by ``module``.

        A class is considered a generator if it defines a callable ``generate``
        attribute. If ``__all__`` is present, only those names are considered.

        Args:
            module (ModuleType): Module to scan for generators.

        Returns:
            GeneratorRegistry: ``self`` for chaining.
        """
        names = list(getattr(module, "__all__", []) or dir(module))
        for attr in names:
            obj = getattr(module, attr, None)
            if isinstance(obj, type) and callable(getattr(obj, "generate", None)):
                self.register(obj)
        return self

    def get_cls(self, name: str) -> type["BaseGenerator"]:
        """Return the class registered for ``name``.

        Args:
            name (str): Canonical name or alias.

        Returns:
            type[BaseGenerator]: Resolved generator class.

        Raises:
            KeyError: If no generator is registered for ``name``.
            # TODO(errors): consider raising UnknownGeneratorError instead of KeyError
        """
        key = self._normalize(name)
        try:
            return self._catalog[key]
        except KeyError as exc:
            available = ", ".join(sorted(self._catalog))
            raise KeyError(f"unknown generator '{name}'. available: {available}") from exc

    def available(self) -> list[str]:
        """Return all registered keys sorted for display."""
        return sorted(self._catalog)

    def resolve(self, name: str) -> type["BaseGenerator"]:
        """Resolve a generator by alias or canonical name.

        Args:
            name (str): Alias or canonical generator name.

        Returns:
            type[BaseGenerator]: Resolved generator class.
        """
        return self.get_cls(name)

    def snapshot(self) -> list[dict[str, Any]]:
        """Return a snapshot of registered generators with metadata.

        The snapshot is a list of dictionaries with keys: ``name`` (canonical
        lowercased class name), ``key`` (the registry alias key), ``aliases``
        (list[str]), and ``doc`` (class docstring, stripped).
        """
        out: list[dict[str, Any]] = []
        for key, cls in sorted(self._catalog.items()):
            meta = getattr(cls, "__meta__", {}) or {}
            alias_meta = meta.get("aliases", ())
            aliases = (
                tuple(alias_meta)
                if isinstance(alias_meta, (list, tuple))
                else tuple(getattr(cls, "__aliases__", ()))
            )
            out.append(
                {
                    "name": cls.__name__.lower(),
                    "key": key,
                    "aliases": list(aliases),
                    "doc": (cls.__doc__ or "").strip(),
                }
            )
        return out
