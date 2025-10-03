import faker_engine.generators as gens
from faker_engine.generators.base import BaseGenerator
# NOTE: kept only for backward-compatibility.
# New code should use faker_engine.core.core
# This file will be removed in the next commit.

class GeneratorRegistry:
    def __init__(self, module=gens):
        self._module = module
        self._instances: dict[
            str, BaseGenerator] = {}

    def load(self):
        for name in getattr(self._module, "__all__", []):
            cls = getattr(self._module, name, None)
            if cls and issubclass(cls, BaseGenerator):
                inst = cls()
                self._instances[name] = inst
                for alias in getattr(cls, "__aliases__", ()):
                    self._instances[alias] = inst

        for cname, aliases in getattr(self._module, "ALIASES", {}).items():
            inst = self._instances.get(cname)
            if inst:
                for alias in aliases:
                    self._instances[alias] = inst
        return self._instances
