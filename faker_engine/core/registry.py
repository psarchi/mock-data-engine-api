from faker_engine.errors import DuplicateAliasError, UnknownGeneratorError, InvalidRegistrationError

class GeneratorRegistry:
    def __init__(self):
        self._catalog = {}

    def register(self, cls, *aliases):
        names = set()
        names.add(cls.__name__.lower())
        for a in getattr(cls, "__aliases__", ()):
            if isinstance(a, str) and a:
                names.add(a.lower())
        for a in aliases:
            if isinstance(a, str) and a:
                names.add(a.lower())

        for name in names:
            if name in self._catalog and self._catalog[name] is not cls:
                raise DuplicateAliasError("Duplicate generator alias: %s" % name)
            self._catalog[name] = cls
        return self

    def register_many(self, pairs):
        for item in pairs:
            if isinstance(item, tuple):
                self.register(*item)
            else:
                self.register(item)
        return self

    def register_from_module(self, module):
        # prefers explicit __all__; falls back to dir(module)
        names = list(getattr(module, "__all__", []) or dir(module))
        for name in names:
            obj = getattr(module, name, None)
            if isinstance(obj, type) and hasattr(obj, "generate"):
                self.register(obj)
        return self

    def get_cls(self, name):
        key = name.strip().lower().replace(" ", "_")
        try:
            return self._catalog[key]
        except KeyError:
            available = ", ".join(sorted(self._catalog))
            raise KeyError(
                "Unknown generator '%s'. Available: %s" % (name, available))

    def available(self):
        return sorted(self._catalog)
