from __future__ import annotations
from typing import Any, get_type_hints
from pydantic import BaseModel, create_model
from pydantic.fields import FieldInfo
from .cache import get_cached, set_cached

# Contracts live here
from faker_engine import contracts as _contracts_pkg


def _all_spec_types() -> dict[str, type]:
    out: dict[str, type] = {}
    for name in getattr(_contracts_pkg, "__all__", []):
        obj = getattr(_contracts_pkg, name, None)
        if isinstance(obj, type) and name.endswith("Spec"):
            out[name] = obj
    # Fallback: scan attributes if __all__ is incomplete
    if not out:
        for attr in dir(_contracts_pkg):
            if not attr.endswith("Spec"):
                continue
            obj = getattr(_contracts_pkg, attr, None)
            if isinstance(obj, type):
                out[attr] = obj
    return out


def _infer_spec_name(gen_name: str) -> str:
    base = gen_name.split(".")[-1]
    if base.endswith("Generator"):
        stem = base
    else:
        stem = f"{base[0].upper()}{base[1:]}Generator"
    return f"{stem}Spec"


def build_model_for_spec(spec_cls: type) -> type[BaseModel]:
    hints = get_type_hints(spec_cls, include_extras=True)
    fields: dict[str, tuple[Any, FieldInfo]] = {}
    for name, anno in hints.items():
        default = getattr(spec_cls, name, ...)
        fields[name] = (anno, default)
    model = create_model(  # type: ignore[call-arg]
        f"{spec_cls.__name__.removesuffix('Spec')}Model",
        __base__=BaseModel,
        __config__={"extra": "forbid", "validate_default": True},
        **fields,  # type: ignore[arg-type]
    )
    return model


def get_model_for(gen_name: str) -> type[BaseModel]:
    cached = get_cached(gen_name)
    if cached is not None:
        return cached
    specs = _all_spec_types()
    spec_name = _infer_spec_name(gen_name)
    spec = specs.get(spec_name)
    if spec is None:
        if spec_name.endswith("GeneratorSpec"):
            spec = specs.get(spec_name)
        else:
            alt = f"{gen_name}Spec"
            spec = specs.get(alt)
    if spec is None:
        raise KeyError(
            f"Spec not found for '{gen_name}' (looked for '{spec_name}')")
    model = build_model_for_spec(spec)
    set_cached(gen_name, model)
    return model
