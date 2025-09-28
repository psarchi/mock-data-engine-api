class SpecBuilder:
    def __init__(self, registry):
        self.registry = registry

    def _normalize(self, spec):
        if isinstance(spec, str):
            return {"type": spec}

        if isinstance(spec, list):
            # keep lists as lists; normalize elements, but don't wrap
            return [self._normalize(s) for s in spec]

        if isinstance(spec, dict):
            clean = {}
            for k, v in spec.items():
                if k == "type":
                    clean[k] = v  # never recurse into 'type' value
                elif isinstance(v, dict) or isinstance(v, list):
                    clean[k] = self._normalize(v)
                else:
                    clean[k] = v
            return clean

        return spec

    def build(self, spec):
        clean = self._normalize(spec)

        if not isinstance(clean, dict) or "type" not in clean:
            raise ValueError("Invalid spec: %r" % spec)

        kind = clean["type"]
        if not isinstance(kind, str):
            raise TypeError("'type' must be string, got %r" % kind)

        cls = self.registry.get_cls(kind)
        return cls.from_spec(self, clean)