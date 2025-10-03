class GeneratorRegistry:
    def __init__(self):
        self._catalog = {}

    def register(self, cls, *aliases):
        names = set(a.lower() for a in aliases)
        names.add(cls.__name__.lower())
        for a in getattr(cls, "__aliases__", ()):
            names.add(a.lower())

        for name in names:
            if name in self._catalog:
                raise KeyError("Duplicate generator alias: %s" % name)
            self._catalog[name] = cls

    def get_cls(self, name):
        key = name.lower()
        try:
            return self._catalog[key]
        except KeyError:
            available = ", ".join(sorted(self._catalog))
            raise KeyError(
                "Unknown generator '%s'. Available: %s" % (name, available))

    def available(self):
        return sorted(self._catalog)
