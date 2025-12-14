from __future__ import annotations

from typing import Any, Dict

from .utils import has_duplicate_items, has_duplicates_in_arrays


def test_duplicate_items_streaming(
    baseline_items: list[Dict[str, Any]],
    chaos_items: list[Dict[str, Any]],
    chaos_applied: list[str],
) -> tuple[bool, Dict[str, Any]]:
    """Test duplicate_items for streaming endpoint.

    PRIMARY: Actual effect - duplicates within arrays or duplicate top-level items
    BONUS: Metadata reporting - chaos_applied should contain 'duplicate_items'
    """
    chaos_has_top_level_dupes = has_duplicate_items(chaos_items)
    chaos_has_array_dupes = has_duplicates_in_arrays(chaos_items)
    has_chaos_metadata = any("duplicate_items" in str(op) for op in chaos_applied)

    actual_effect_detected = chaos_has_top_level_dupes or chaos_has_array_dupes
    passed = actual_effect_detected

    data = {
        "chaos_has_top_level_dupes": chaos_has_top_level_dupes,
        "chaos_has_array_dupes": chaos_has_array_dupes,
        "actual_effect_detected": actual_effect_detected,
        "chaos_metadata_reported": has_chaos_metadata,
    }

    warnings = []
    if has_chaos_metadata and not actual_effect_detected:
        warnings.append("Metadata reports chaos but no duplicates detected")
    elif not has_chaos_metadata and actual_effect_detected:
        warnings.append("Duplicates detected but not reported in metadata")

    if warnings:
        data["warnings"] = warnings

    return passed, data


def test_duplicate_items_rest(
    baseline_items: list[Dict[str, Any]],
    chaos_items: list[Dict[str, Any]],
    chaos_applied: list[str],
) -> tuple[bool, Dict[str, Any]]:
    """Test duplicate_items for REST endpoint."""
    return test_duplicate_items_streaming(baseline_items, chaos_items, chaos_applied)

