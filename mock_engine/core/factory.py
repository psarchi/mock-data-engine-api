from __future__ import annotations

from typing import TYPE_CHECKING, Any

from mock_engine.core.errors import MissingConfigureMethodError
from mock_engine.core.registry import GeneratorRegistry

if TYPE_CHECKING:
    from mock_engine.generators.base import BaseGenerator


# TODO(arch): depend on a registry *protocol* instead of the concrete class
# (e.g., an interface with ``get_cls(name: str) -> type[BaseGenerator]``)
class GeneratorFactory:
    """Factory for instantiating and configuring registered generators.
        Resolves a generator class from the registry, instantiates it, and calls its
        ``configure(**kwargs)`` method to return a configured instance.
    Args:
        registry (GeneratorRegistry): Registry used to resolve generator classes.
    """

    def __init__(self, registry: GeneratorRegistry) -> None:
        """Initialize the factory with a generator registry.

        Args:
            registry (GeneratorRegistry): Registry used to resolve names to implementations.
        """
        self._registry: GeneratorRegistry = registry

    def resolve(self, name: str, **kwargs: Any) -> BaseGenerator:
        """Resolve, instantiate, and configure a generator by name.

        Looks up the generator class in the registry, constructs an instance,
        and calls ``configure(**kwargs)`` on it. The configured instance is
        returned.

        Args:
            name (str): Canonical generator name or alias.
            **kwargs (Any): Keyword arguments forwarded to ``configure``.

        Returns:
            BaseGenerator: Configured generator instance.

        Raises:
            MissingConfigureMethodError: The resolved generator instance has no
                callable ``configure`` method.
        """
        cls = self._registry.get_cls(name)
        instance: BaseGenerator = cls()
        configure = getattr(instance, "configure", None)
        if not callable(configure):
            # TODO(errors): consider raising a more specific error with the missing method signature
            raise MissingConfigureMethodError(f"{cls.__name__} has no configure() method")
        return configure(**kwargs)
