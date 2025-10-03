import faker_engine.generators as gens
from faker_engine.generators.base import BaseGenerator
from faker_engine.generators.legacy_registry import GeneratorRegistry


class GeneratorCore:
    def __init__(self, module=gens):
        self._instances = GeneratorRegistry(module).load()

    def _sanity_check(self, instance):
        if not callable(getattr(instance, 'configure', None)):
            raise TypeError(
                f"Generator {instance.__class__.__name__} has no configure function")

    def resolve(self, name: str, *args, **kwargs) -> BaseGenerator:
        name = name.strip().lower().replace(" ", "_")
        self._sanity_check(self._instances[name])

        try:
            return self._instances[name].configure(*args, **kwargs)
        except KeyError:
            available = ", ".join(sorted(self._instances))
            raise KeyError(
                f"Unknown generator '{name}'. Available: {available}")

