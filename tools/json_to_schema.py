#!/usr/bin/env python3
"""Translate JSON example data to YAML schema format.

Usage:
    python tools/json_to_schema.py < example.json > schema.yaml
    python tools/json_to_schema.py example.json -o schema.yaml
    python tools/json_to_schema.py example.json --infer-arrays --sample-size 10
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from typing import Any

import yaml


def infer_type_from_value(value: Any, parent_key: str = "") -> dict[str, Any]:
    """Infer schema type from a single value."""
    if value is None:
        return {"type": "maybe", "p_null": 0.5, "child": {"type": "string"}}

    if isinstance(value, bool):
        return {"type": "bool"}

    if isinstance(value, int):
        return {"type": "int", "min": value, "max": value}

    if isinstance(value, float):
        return {"type": "float", "min": value, "max": value, "precision": 2}

    if isinstance(value, str):
        # Try to detect common patterns
        if value.isdigit():
            return {"type": "string", "regex": r"^\d+$"}
        if "@" in value and "." in value:
            return {"type": "string", "string_type": "email"}
        if value.startswith("http://") or value.startswith("https://"):
            return {"type": "string", "string_type": "url"}
        # Default to generic string
        return {"type": "string"}

    if isinstance(value, list):
        if not value:
            return {
                "type": "array",
                "min_items": 0,
                "max_items": 0,
                "child": {"type": "string"},
            }

        # Sample first item for child type
        child_schema = infer_type_from_value(value[0], parent_key)
        return {
            "type": "array",
            "min_items": len(value),
            "max_items": len(value),
            "child": child_schema,
        }

    if isinstance(value, dict):
        fields = {}
        for key, val in value.items():
            fields[key] = infer_type_from_value(val, key)
        return {"type": "object", "fields": fields}

    # Fallback
    return {"type": "string"}


def merge_schemas(schemas: list[dict[str, Any]]) -> dict[str, Any]:
    """Merge multiple inferred schemas into one (for array item analysis)."""
    if not schemas:
        return {"type": "string"}

    # Count types
    types = Counter(s["type"] for s in schemas)
    most_common_type = types.most_common(1)[0][0]

    # Start with first schema of most common type
    base_schema = next((s for s in schemas if s["type"] == most_common_type), schemas[0])
    merged = dict(base_schema)

    # For numeric types, expand min/max ranges
    if most_common_type in ("int", "float"):
        mins = [s.get("min", 0) for s in schemas if s["type"] == most_common_type]
        maxs = [s.get("max", 100) for s in schemas if s["type"] == most_common_type]
        if mins:
            merged["min"] = min(mins)
        if maxs:
            merged["max"] = max(maxs)

    # For arrays, expand item count range
    if most_common_type == "array":
        min_items = [
            s.get("min_items", 0) for s in schemas if s["type"] == "array"
        ]
        max_items = [
            s.get("max_items", 10) for s in schemas if s["type"] == "array"
        ]
        if min_items:
            merged["min_items"] = min(min_items)
        if max_items:
            merged["max_items"] = max(max_items)

    # For objects, merge fields
    if most_common_type == "object":
        all_fields = {}
        for schema in schemas:
            if schema["type"] == "object" and "fields" in schema:
                for field_name, field_schema in schema["fields"].items():
                    if field_name not in all_fields:
                        all_fields[field_name] = []
                    all_fields[field_name].append(field_schema)

        merged_fields = {}
        for field_name, field_schemas in all_fields.items():
            merged_fields[field_name] = merge_schemas(field_schemas)

        merged["fields"] = merged_fields

    return merged


def infer_schema_from_samples(
    samples: list[Any], infer_arrays: bool = False
) -> dict[str, Any]:
    """Infer schema from multiple sample objects."""
    if not samples:
        return {"type": "object", "fields": {}}

    # Infer schema from each sample
    schemas = [infer_type_from_value(sample) for sample in samples]

    # If analyzing array items and infer_arrays is True, merge them
    if infer_arrays and len(samples) > 1:
        return merge_schemas(schemas)

    # Otherwise, just use the first sample
    return schemas[0]


def json_to_schema(
    data: Any, infer_arrays: bool = False, sample_size: int = 10
) -> dict[str, Any]:
    """Convert JSON data to schema YAML format.

    Args:
        data: JSON data (dict, list, or primitive)
        infer_arrays: If True, analyze multiple array items to infer schema
        sample_size: Number of array items to sample when inferring

    Returns:
        Schema dict in YAML format
    """
    if isinstance(data, list):
        # If it's a list of objects, treat each as a sample
        samples = data[:sample_size] if infer_arrays else [data[0] if data else {}]
        schema = infer_schema_from_samples(samples, infer_arrays)
    else:
        schema = infer_type_from_value(data)

    return schema


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Translate JSON example to YAML schema format"
    )
    parser.add_argument(
        "input", nargs="?", help="Input JSON file (default: stdin)", default="-"
    )
    parser.add_argument(
        "-o", "--output", help="Output YAML file (default: stdout)", default="-"
    )
    parser.add_argument(
        "--infer-arrays",
        action="store_true",
        help="Analyze multiple array items to infer schema",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=10,
        help="Number of array items to sample (default: 10)",
    )
    args = parser.parse_args()

    # Read input
    try:
        if args.input == "-":
            data = json.load(sys.stdin)
        else:
            with open(args.input, "r") as f:
                data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON: {e}", file=sys.stderr)
        return 1
    except FileNotFoundError:
        print(f"Error: File not found: {args.input}", file=sys.stderr)
        return 1

    # Convert to schema
    schema = json_to_schema(data, args.infer_arrays, args.sample_size)

    # Write output
    yaml_str = yaml.dump(schema, default_flow_style=False, sort_keys=False)

    if args.output == "-":
        print(yaml_str)
    else:
        with open(args.output, "w") as f:
            f.write(yaml_str)
        print(f"Schema written to {args.output}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
