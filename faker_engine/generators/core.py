import gens
from faker_engine.generators.gens.base import BaseGenerator
from faker_engine.generators.context import GenContext
from faker_engine.generators.registry import GeneratorRegistry


class GeneratorCore:
    def __init__(self, module=gens):
        self._instances, self._canon = GeneratorRegistry(module).load()

    def _sanity_check(self, instance):
        if not callable(getattr(instance, 'configure', None)):
            raise TypeError(
                f"Generator {instance.__class__.__name__} has no configure function")

    def resolve(self, name: str, **kwargs) -> BaseGenerator:
        name = name.strip().lower().replace(" ", "_")
        self._sanity_check(self._instances[name])

        try:
            return self._instances[name].configure(**kwargs)
        except KeyError:
            available = ", ".join(sorted(self._instances))
            raise KeyError(
                f"Unknown generator '{name}'. Available: {available}")
