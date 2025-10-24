from __future__ import annotations
from typing import Any

LEAF_DEFAULT_KEYS = ("status", "value", "range", "map", "list", "enum")


def is_leaf_spec(node: Any) -> bool:
    return isinstance(node, dict) and any(k in node for k in LEAF_DEFAULT_KEYS)


def _validate_leaf(node: dict, path: list[str], errors: list[str]) -> None:
    present = [k for k in LEAF_DEFAULT_KEYS if k in node]
    if len(present) == 0:
        errors.append(
            f"missing default key at {'.'.join(path) or 'root'} (one of: {', '.join(LEAF_DEFAULT_KEYS)})")
    elif len(present) > 1:
        errors.append(
            f"multiple default keys {present} at {'.'.join(path) or 'root'}")
    if "accepts" not in node or not isinstance(node.get("accepts"), str):
        errors.append(
            f"missing or invalid 'accepts' at {'.'.join(path) or 'root'}")
    if "description" not in node or not isinstance(node.get("description"),
                                                   str):
        errors.append(
            f"missing or invalid 'description' at {'.'.join(path) or 'root'}")


def _walk(tree: Any, path: list[str], errors: list[str]) -> None:
    if isinstance(tree, dict):
        if is_leaf_spec(tree):
            _validate_leaf(tree, path, errors)
        for k, v in tree.items():
            if isinstance(k, str):
                _walk(v, path + [k], errors)
    elif isinstance(tree, list):
        for i, v in enumerate(tree):
            _walk(v, path + [str(i)], errors)


def validate_default_yaml_schema(root_mapping: dict) -> None:
    errors: list[str] = []
    _walk(root_mapping, [], errors)
    if errors:
        raise ValueError(
            "Invalid default.yaml schema:\n- " + "\n- ".join(errors))
