from __future__ import annotations

from collections.abc import Mapping
import enum
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, create_model

from faker_engine.config.schema import LEAF_DEFAULT_KEYS, is_leaf_spec

# TODO: move this to schemas or constants module?
# Aliases accepted in "accepts" strings.
_ACCEPTS_ALIASES: dict[str, str] = {
    "true/false": "bool",
    "boolean": "bool",
    "list of ints": "list[int]",
    "list of floats": "list[float]",
    "list of strings": "list[str]",
}

# Primitive type map for "accepts" strings.
_PRIMITIVE_MAP: dict[str, type[object]] = {
    "bool": bool,
    "int": int,
    "float": float,
    "str": str,
}

# Patterns for structured "accepts" types.
_ENUM_RE = re.compile(r"^enum\[(.+)\]$")
_TUPLE_RE = re.compile(r"^tuple\[(.+)\]$")
_LIST_RE = re.compile(r"^list\[(.+)\]$")
_MAP_RE = re.compile(r"^map\[(.+?),(.+?)\]$")


class _AllowExtra(BaseModel):
    """Pydantic base model that allows extra keys."""

    model_config = ConfigDict(extra="allow")


def _norm_accepts(accepts_str: str) -> str:
    """Normalize an 'accepts' string by applying known aliases and trimming.

    Args:
        accepts_str (str): Raw accepts string from the spec.

    Returns:
        str: Normalized accepts string.
    """
    return _ACCEPTS_ALIASES.get(accepts_str.strip().lower(), accepts_str.strip())


def _parse_type(accepts: str) -> object:
    """Parse a normalized 'accepts' string into a Python/typing construct.

    Supported forms:
        - Primitives: ``bool``, ``int``, ``float``, ``str``
        - Tuples: ``tuple[int, str]`` (exactly two items)
        - Lists: ``list[int]``
        - Maps: ``map[str,int]``
        - Enums: ``enum[a, b, c]`` (auto-builds an Enum type)

    Args:
        accepts (str): Normalized accepts string.

    Returns:
        object: A type-like object (primitive, typing alias, or Enum subclass).

    Raises:
        ValueError: If the accepts string is malformed or unknown.
    """
    accepts = _norm_accepts(accepts)

    # Primitive
    if accepts in _PRIMITIVE_MAP:
        return _PRIMITIVE_MAP[accepts]

    # Tuple
    match_tuple = _TUPLE_RE.match(accepts)
    if match_tuple:
        tuple_parts = [part.strip() for part in match_tuple.group(1).split(",")]
        if len(tuple_parts) != 2:
            raise ValueError(f"only tuple of 2 supported in accepts: {accepts}")
        return tuple[
            _PRIMITIVE_MAP[tuple_parts[0]],
            _PRIMITIVE_MAP[tuple_parts[1]],
        ]

    # List
    match_list = _LIST_RE.match(accepts)
    if match_list:
        element_token = match_list.group(1).strip()
        return list[_PRIMITIVE_MAP[element_token]]

    # Map
    match_map = _MAP_RE.match(accepts)
    if match_map:
        key_token = match_map.group(1).strip()
        value_token = match_map.group(2).strip()
        return dict[_PRIMITIVE_MAP[key_token], _PRIMITIVE_MAP[value_token]]

    # Enum
    match_enum = _ENUM_RE.match(accepts)
    if match_enum:
        enum_tokens = [token.strip() for token in match_enum.group(1).split(",") if token.strip()]

        def _safe_name(value_text: str) -> str:
            """Coerce an enum member value to a valid Python identifier.

            Args:
                value_text (str): Original enum member text.

            Returns:
                str: Safe, uppercase member name.
            """
            identifier = re.sub(r"[^a-zA-Z0-9]+", "_", value_text).strip("_").upper() or "VAL"
            if identifier and identifier[0].isdigit():
                identifier = f"V_{identifier}"
            return identifier

        members = {
            _safe_name(token): int(token) if token.isdigit() else token for token in enum_tokens
        }
        dyn_enum = enum.Enum(
            f"CfgEnum_{abs(hash(tuple(enum_tokens))) % 10 ** 8}", members
        )
        return dyn_enum

    raise ValueError(f"unknown accepts type: {accepts}")


def _extract_default(node: Mapping[str, Any]) -> Any:
    """Extract the default value from a leaf spec node.

    Args:
        node (Mapping[str, Any]): Leaf node mapping.

    Returns:
        Any: Default value if present; otherwise ``None``.
    """
    for default_key in LEAF_DEFAULT_KEYS:
        if default_key in node:
            return node[default_key]
    return None


def _is_group(node: object) -> bool:
    """Return True when the node is a non-leaf mapping (i.e. a group).

    Args:
        node (object): Node to test.

    Returns:
        bool: True if the node is a mapping and not a leaf spec.
    """
    return isinstance(node, dict) and (not is_leaf_spec(node))


def _model_name_from_path(path: tuple[str, ...] | None) -> str:
    """Build a Pydantic model name from a tree path.

    Args:
        path (tuple[str, ...] | None): Path segments from the root.

    Returns:
        str: Model name derived from the path.
    """
    if not path:
        return "SettingsModel"
    return "Cfg_" + "_".join(segment.capitalize().replace("-", "_") for segment in path)


def build_model_from_default(
    tree: Mapping[str, Any],
) -> tuple[type[BaseModel], dict[str, Any], dict[str, Any]]:
    """Create a Pydantic model and defaults from a default-spec tree.

    The function walks the tree, translating leaf specs into typed fields with
    defaults and metadata, and groups into nested Pydantic models that allow
    extra keys.

    Args:
        tree (Mapping[str, Any]): Default-spec mapping.

    Returns:
        tuple[type[BaseModel], dict[str, Any], dict[str, Any]]: A tuple of:
            - model (type[BaseModel]): Root Pydantic model subclass.
            - defaults (dict[str, Any]): Defaults tree aligned with the model.
            - meta (dict[str, Any]): Per-field metadata (accepts/description).
    """

    def walk(node: object, path: tuple[str, ...]) -> tuple[object, Any, dict[str, Any]]:
        """Recursively build field or model definitions for a subtree.

        Args:
            node (object): Current subtree node.
            path (tuple[str, ...]): Path from the root to the current node.

        Returns:
            tuple[object, Any, dict[str, Any]]: (type_or_model, default_value, field_meta)
        """
        if is_leaf_spec(node):  # type: ignore[arg-type]
            accepts = node.get("accepts", "")  # type: ignore[assignment]
            type_or_model = _parse_type(accepts)
            default_value = _extract_default(node)  # type: ignore[arg-type]
            field_meta = {
                "accepts": accepts,
                "description": node.get("description", ""),
            }  # type: ignore[attr-defined]
            return type_or_model, default_value, field_meta

        if _is_group(node):
            assert isinstance(node, dict)
            fields: dict[str, tuple[object, Field]] = {}
            defaults_dict: dict[str, Any] = {}
            meta_group: dict[str, Any] = {}

            for key, value in node.items():
                if key in {"group_mode"}:
                    continue
                type_or_model, default_value, field_meta = walk(value, (*path, key))
                fields[key] = (type_or_model, Field(default=default_value))
                defaults_dict[key] = (
                    default_value
                    if default_value is not None
                    else ({} if isinstance(value, dict) else None)
                )
                meta_group[key] = field_meta

            model_name = _model_name_from_path(path)
            model = create_model(model_name, __base__=_AllowExtra, **fields)
            return model, defaults_dict, meta_group

        return Any, node, {"description": "", "accepts": "any"}

    model_obj, defaults, meta = walk(tree, ())
    if not (isinstance(model_obj, type) and issubclass(model_obj, BaseModel)):
        root_model = create_model(
            "SettingsModel",
            __base__=_AllowExtra,
            root=(type(model_obj), Field(default=defaults)),
        )
        return root_model, {"root": defaults}, {"root": meta}

    return model_obj, defaults, meta
