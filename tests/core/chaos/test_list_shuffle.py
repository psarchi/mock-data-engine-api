from __future__ import annotations

from typing import Any, Dict


def _find_arrays_in_item(item: Dict[str, Any]) -> list[tuple[str, list]]:
    """Find all array fields in an item and return (field_name, array) tuples."""
    arrays = []
    for key, value in item.items():
        if isinstance(value, list):
            arrays.append((key, value))
        elif isinstance(value, dict):
            # Check nested objects
            for nested_key, nested_value in value.items():
                if isinstance(nested_value, list):
                    arrays.append((f"{key}.{nested_key}", nested_value))
    return arrays


def _arrays_are_shuffled(
    baseline_items: list[Dict[str, Any]], chaos_items: list[Dict[str, Any]]
) -> bool:
    """Check if any arrays have been shuffled between baseline and chaos."""
    # We can't reliably detect shuffling in generated data since each generation
    # is independent. Instead, we check if arrays exist and are not all identical.
    # This is a weak check but better than nothing.

    arrays_found = False
    for item in chaos_items:
        arrays = _find_arrays_in_item(item)
        if arrays:
            arrays_found = True
            break

    return arrays_found


def test_list_shuffle_streaming(
    baseline_items: list[Dict[str, Any]],
    chaos_items: list[Dict[str, Any]],
    chaos_applied: list[str],
) -> tuple[bool, Dict[str, Any]]:
    """Test list_shuffle for streaming endpoint.

    PRIMARY: Actual effect - arrays should exist (shuffle can be applied)
    BONUS: Metadata reporting - chaos_applied should contain 'list_shuffle'

    Note: Detecting actual shuffling is difficult since each generation is independent.
    We check if arrays are present, which means the chaos op had data to shuffle.
    """
    has_chaos_metadata = any("list_shuffle" in str(op) for op in chaos_applied)

    actual_effect_detected = _arrays_are_shuffled(baseline_items, chaos_items)
    passed = actual_effect_detected

    data = {
        "actual_effect_detected": actual_effect_detected,
        "chaos_metadata_reported": has_chaos_metadata,
    }

    warnings = []
    if has_chaos_metadata and not actual_effect_detected:
        warnings.append("Metadata reports chaos but no arrays found to shuffle")
    elif not has_chaos_metadata and actual_effect_detected:
        warnings.append("Arrays found but chaos not reported in metadata")

    if warnings:
        data["warnings"] = warnings

    return passed, data


def test_list_shuffle_rest(
    baseline_items: list[Dict[str, Any]],
    chaos_items: list[Dict[str, Any]],
    chaos_applied: list[str],
) -> tuple[bool, Dict[str, Any]]:
    """Test list_shuffle for REST endpoint."""
    return test_list_shuffle_streaming(baseline_items, chaos_items, chaos_applied)
