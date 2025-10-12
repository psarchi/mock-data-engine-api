try:
    from pydantic import BaseModel, create_model, Field, ConfigDict
except Exception as e:
    BaseModel = object  # type: ignore


    def create_model(*args, **kwargs):
        raise ImportError("Pydantic v2 required")


    class Field:  # type: ignore
        def __init__(self, *a, **k): ...


    class ConfigDict(dict):
        ...


def model_from_cache(cache_entry):
    fields = cache_entry.get("fields", {}) or {}
    aliases = cache_entry.get("aliases", {}) or {}

    model_fields = {}

    def _guess_type(t):
        if isinstance(t, str):
            return {"int": int, "float": float, "str": str, "bool": bool,
                    "Any": object}.get(t, object)
        return t or object

    alias_map = {}
    if isinstance(aliases, dict):
        for a, canonical in aliases.items():
            alias_map.setdefault(canonical, []).append(a)

    for fname, meta in fields.items():
        typ = _guess_type(meta.get("type"))
        required = bool(meta.get("required", False))
        default = meta.get("default", ... if required else None)
        alias = (alias_map.get(fname) or [None])[0]
        model_fields[fname] = (
        typ, Field(... if required else default, alias=alias))

    Model = create_model(
        cache_entry.get("name", "GeneratorModel"),
        __config__=ConfigDict(extra='forbid', strict=True,
                              populate_by_name=True),
        **model_fields,  # type: ignore
    )
    return Model  # type: ignore
