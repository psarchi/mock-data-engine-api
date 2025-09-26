import gens
from faker_engine.generators.gens.base import BaseGenerator


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
