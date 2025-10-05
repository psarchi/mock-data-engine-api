from faker_engine.errors import MissingTypeError, UnknownTypeError, InvalidSpecStructureError, NormalizationError
class SpecBuilder:
    def __init__(self, registry):
        self.registry = registry


    def _normalize(self, spec, path="root"):
        if isinstance(spec, str):
            return {"type": spec}
        if isinstance(spec, list):
            return [self._normalize(s, path=path+"[]") for s in spec]
        if isinstance(spec, dict):
            clean = {}
            for field_name, field_spec in spec.items():
                if field_name == "type":
                    clean[field_name] = field_spec
                elif isinstance(field_spec, (dict, list)):
                    next_path = f"{path}.{field_name}"
                    clean[field_name] = self._normalize(field_spec, path=next_path)
                else:
                    clean[field_name] = field_spec
            return clean
        return spec

    def build(self, spec, path="root"):
        clean = self._normalize(spec, path=path)
        if not isinstance(clean, dict) or "type" not in clean:
            raise MissingTypeError("Invalid spec (missing 'type')", path=path)
        kind = clean["type"]
        if not isinstance(kind, str):
            raise InvalidSpecStructureError("'type' must be string", path=path)
        try:
            cls = self.registry.get_cls(kind)
        except Exception as e:
            raise UnknownTypeError(str(e), path=path)
        return cls.from_spec(self, clean)
