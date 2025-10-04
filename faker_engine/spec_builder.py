class SpecBuilder:
    def __init__(self, factory):
        self.factory = factory

    def _normalize(self, spec):
        if isinstance(spec, str):
            # bare sugar: just a type name
            return {"type": spec}

        if isinstance(spec, list):
            return [self._normalize(s) for s in spec]

        if isinstance(spec, dict):
            clean = {}
            for field_name, field_spec in spec.items():
                if field_name == "type":
                    clean[field_name] = field_spec  # leave type as-is
                elif isinstance(field_spec, (dict, list)):
                    clean[field_name] = self._normalize(field_spec)
                else:
                    clean[field_name] = field_spec
            return clean

        return spec

    def build(self, spec):
        clean = self._normalize(spec)

        if not isinstance(clean, dict) or "type" not in clean:
            raise ValueError(f"Invalid spec: {spec}")

        kind = clean["type"]
        if not isinstance(kind, str):
            raise TypeError(f"'type' must be string, got {kind!r}")

        cls = self.factory._catalog[kind]
        return cls.from_spec(self, clean)
