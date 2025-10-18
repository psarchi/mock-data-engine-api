from __future__ import annotations
from typing import Any, get_type_hints, get_origin, get_args, Union
from pydantic import BaseModel, create_model
from pydantic.config import ConfigDict
from pydantic.types import StrictInt, StrictFloat, StrictBool
import importlib


class ModelProvider:
    def __init__(self) -> None:
        self._contracts = importlib.import_module('faker_engine.contracts')
        self._cache: dict[str, type[BaseModel]] = {}

    def _all_specs(self) -> dict[str, type]:
        out: dict[str, type] = {}
        for name in getattr(self._contracts, "__all__", []):
            obj = getattr(self._contracts, name, None)
            if isinstance(obj, type) and name.endswith("Spec"):
                out[name] = obj
        if not out:
            for attr in dir(self._contracts):
                if not attr.endswith("Spec"):
                    continue
                obj = getattr(self._contracts, attr, None)
                if isinstance(obj, type):
                    out[attr] = obj
        return out

    def _infer_spec_name(self, gen_name: str) -> str:
        base = gen_name.split('.')[-1]
        stem = base if base.endswith(
            'Generator') else f"{base[:1].upper()}{base[1:]}Generator"
        return f"{stem}Spec"

    def _strictify(self, tp):
        origin = get_origin(tp)
        if origin is None:
            if tp is int: return StrictInt
            if tp is float: return StrictFloat
            if tp is bool: return StrictBool
            return tp
        args = tuple(self._strictify(a) for a in get_args(tp))
        try:
            if origin is Union:
                return Union[args]  # type: ignore[arg-type]
            if hasattr(origin, '__getitem__'):
                return origin[args]
        except Exception:
            return tp
        return tp

    def get(self, gen_name: str) -> type[BaseModel]:
        if gen_name in self._cache:
            return self._cache[gen_name]
        specs = self._all_specs()
        spec_cls = specs.get(self._infer_spec_name(gen_name))
        if spec_cls is None:
            raise KeyError(f"Spec not found for '{gen_name}'")
        hints = get_type_hints(spec_cls, include_extras=True)
        fields: dict[str, tuple[Any, Any]] = {}
        for name, anno in hints.items():
            strict_anno = self._strictify(anno)
            default = getattr(spec_cls, name, ...)
            fields[name] = (strict_anno, default)
        model = create_model(  # type: ignore[call-arg]
            f"{spec_cls.__name__.removesuffix('Spec')}Model",
            __base__=BaseModel,
            **fields,  # type: ignore[arg-type]
        )
        # strict config
        model.model_config = ConfigDict(extra='forbid', validate_default=True)
        self._cache[gen_name] = model
        return model
