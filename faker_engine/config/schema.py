"""Schema validation utilities for default configuration specs.

Validates that each leaf node contains exactly one default key and the required
metadata (``accepts`` and ``description``), and that the overall structure is a
nested mapping/list tree.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

# Keys that indicate a defaulted leaf specification.
LEAF_DEFAULT_KEYS: tuple[str, ...] = ("status", "value", "range", "map", "list", "enum")


def is_leaf_spec(node: Any) -> bool:
    """Return ``True`` when ``node`` is a mapping with exactly one default key.

    Args:
        node (Any): Candidate node from the spec tree.

    Returns:
        bool: ``True`` if ``node`` looks like a leaf spec; otherwise ``False``.
    """
    return isinstance(node, dict) and any(key in node for key in LEAF_DEFAULT_KEYS)


# TODO(utils): if tree walking is needed elsewhere, consider moving validation walk helpers to a shared utils module

def _validate_leaf(node: Mapping[str, Any], path: tuple[str, ...], errors: list[str]) -> None:
    """Validate a single leaf node.

    Ensures exactly one default key is present and both ``accepts`` and
    ``description`` are valid strings.

    Args:
        node (Mapping[str, Any]): Leaf node mapping.
        path (tuple[str, ...]): Schema location for error reporting.
        errors (list[str]): Mutable list to collect error messages.
    """
    present_default_keys = [key for key in LEAF_DEFAULT_KEYS if key in node]
    location = ".".join(path) or "root"

    if len(present_default_keys) == 0:
        errors.append(
            "missing default key at "
            f"{location} (one of: {', '.join(LEAF_DEFAULT_KEYS)})"
        )
    elif len(present_default_keys) > 1:
        errors.append(f"multiple default keys {present_default_keys} at {location}")

    if "accepts" not in node or not isinstance(node.get("accepts"), str):
        errors.append(f"missing or invalid 'accepts' at {location}")
    if "description" not in node or not isinstance(node.get("description"), str):
        errors.append(f"missing or invalid 'description' at {location}")


def _walk(tree: Any, path: tuple[str, ...], errors: list[str]) -> None:
    """Recursively walk the spec tree and validate all leaves.

    Args:
        tree (Any): Current subtree (mapping, list, or primitive).
        path (tuple[str, ...]): Location path from the root.
        errors (list[str]): Mutable list to collect error messages.
    """
    if isinstance(tree, dict):
        if is_leaf_spec(tree):
            _validate_leaf(tree, path, errors)
        for key, value in tree.items():
            if isinstance(key, str):
                _walk(value, path + (key,), errors)
    elif isinstance(tree, list):
        for index, value in enumerate(tree):
            _walk(value, path + (str(index),), errors)


def validate_default_yaml_schema(root_mapping: Mapping[str, Any]) -> None:
    """Validate the structure and leaf requirements of ``default.yaml``.

    Args:
        root_mapping (Mapping[str, Any]): Parsed YAML root mapping.

    Raises:
        ValueError: If the schema is invalid.
        # TODO(errors): consider raising DefaultSchemaError (errors.DefaultSchemaError) instead of ValueError
    """
    errors: list[str] = []
    _walk(root_mapping, (), errors)
    if errors:
        raise ValueError("Invalid default.yaml schema:\n- " + "\n- ".join(errors))
