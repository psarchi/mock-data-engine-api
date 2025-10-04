from .registry import GeneratorRegistry


class GeneratorFactory:
    def __init__(self, registry):
        if not isinstance(registry, GeneratorRegistry):
            raise TypeError("registry must be a GeneratorRegistry")
        self._registry = registry

    def resolve(self, name, **kwargs):
        cls = self._registry.get_cls(name)
        inst = cls()
        configure = getattr(inst, "configure", None)
        if not callable(configure):
            raise TypeError("%s has no configure()" % cls.__name__)
        return configure(**kwargs)
