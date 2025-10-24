from __future__ import annotations
from typing import Any, Dict, Tuple, List, Mapping, get_args, get_origin
from pydantic import BaseModel, Field, ConfigDict, create_model
from typing import Literal
import re

from .schema import is_leaf_spec, LEAF_DEFAULT_KEYS

_ACCEPTS_ALIASES = {
    "true/false": "bool",
    "boolean": "bool",
    "list of ints": "list[int]",
    "list of floats": "list[float]",
    "list of strings": "list[str]",
}

_primitive_map = {"bool": bool, "int": int, "float": float, "str": str}


def _norm_accepts(s: str) -> str:
    return _ACCEPTS_ALIASES.get(s.strip().lower(), s.strip())


_enum_re = re.compile(r"^enum\[(.+)\]$")
_tuple_re = re.compile(r"^tuple\[(.+)\]$")
_list_re = re.compile(r"^list\[(.+)\]$")
_map_re = re.compile(r"^map\[(.+?),(.+?)\]$")


def _parse_type(accepts: str):
    accepts = _norm_accepts(accepts)
    if accepts in _primitive_map:
        return _primitive_map[accepts]
    m = _tuple_re.match(accepts)
    if m:
        inner = [x.strip() for x in m.group(1).split(",")]
        if len(inner) != 2:
            raise ValueError(
                f"only tuple of 2 supported in accepts: {accepts}")
        return Tuple[
            _primitive_map[inner[0]], _primitive_map[inner[1]]]  # type: ignore
    m = _list_re.match(accepts)
    if m:
        inner = m.group(1).strip()
        return List[_primitive_map[inner]]  # type: ignore
    m = _map_re.match(accepts)
    if m:
        k = m.group(1).strip()
        v = m.group(2).strip()
        return Dict[_primitive_map[k], _primitive_map[v]]  # type: ignore
    m = _enum_re.match(accepts)
    if m:
        raw = [x.strip() for x in m.group(1).split(",") if x.strip()]
        are_ints = all(r.isdigit() for r in raw)
        if are_ints:
            vals = tuple(int(r) for r in raw)
        else:
            vals = tuple(raw)
        return Literal[vals]  # type: ignore
    raise ValueError(f"unknown accepts type: {accepts}")


def _extract_default(node: dict) -> Any:
    for key in LEAF_DEFAULT_KEYS:
        if key in node:
            return node[key]
    return None


def _is_group(node: Any) -> bool:
    return isinstance(node, dict) and not is_leaf_spec(node)


def _model_name_from_path(path: List[str]) -> str:
    if not path:
        return "SettingsModel"
    return "Cfg_" + "_".join(p.capitalize().replace("-", "_") for p in path)


def build_model_from_default(tree: Mapping[str, Any]):
    def walk(node: Any, path: List[str]):
        if is_leaf_spec(node):
            accepts = node.get("accepts", "")
            t = _parse_type(accepts)
            default = _extract_default(node)
            meta = {"accepts": accepts,
                    "description": node.get("description", "")}
            return t, default, meta
        elif _is_group(node):
            fields = {}
            defaults_dict = {}
            meta_group = {}
            for k, v in node.items():
                if k in ("group_mode",):  # reserved keys for future
                    continue
                t, d, m = walk(v, path + [k])
                fields[k] = (t, Field(default=d))
                defaults_dict[k] = d if d is not None else (
                    {} if isinstance(v, dict) else None)
                meta_group[k] = m
            model_name = _model_name_from_path(path)
            model = create_model(model_name, __config__=type("Cfg", (), {   # type: ignore
                "extra": "allow"}), **fields)
            return model, defaults_dict, meta_group
        else:
            return Any, node, {"description": "", "accepts": "any"}

    model, defaults, meta = walk(tree, [])
    if not (isinstance(model, type) and issubclass(model, BaseModel)):
        # wrap as root model
        root_model = create_model("SettingsModel", __config__=type("Cfg", (), {   # type: ignore
            "extra": "allow"}), root=(
            type(model), Field(default=defaults)))
        return root_model, {"root": defaults}, {"root": meta}
    return model, defaults, meta
