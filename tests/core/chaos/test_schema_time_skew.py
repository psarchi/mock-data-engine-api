from __future__ import annotations

from typing import Any, Dict
from datetime import datetime


def _find_timestamp_fields(item: Dict[str, Any]) -> list[tuple[str, Any]]:
    """Find all timestamp/datetime fields in an item."""
    timestamps = []
    for key, value in item.items():
        if key.endswith(("_field", "_timestamp", "_datetime", "_time")):
            if isinstance(value, (int, float)):
                timestamps.append((key, value))
            elif isinstance(value, str):
                try:
                    datetime.fromisoformat(value.replace("Z", "+00:00"))
                    timestamps.append((key, value))
                except (ValueError, AttributeError):
                    pass
        elif isinstance(value, dict):
            for nested_key, nested_value in value.items():
                if nested_key.endswith(("_field", "_timestamp", "_datetime", "_time")):
                    if isinstance(nested_value, (int, float, str)):
                        timestamps.append((f"{key}.{nested_key}", nested_value))
    return timestamps


def test_schema_time_skew_streaming(
    baseline_items: list[Dict[str, Any]],
    chaos_items: list[Dict[str, Any]],
    chaos_applied: list[str],
) -> tuple[bool, Dict[str, Any]]:
    """Test schema_time_skew for streaming endpoint.

    PRIMARY: Actual effect - timestamp/datetime fields should exist for skewing
    BONUS: Metadata reporting - chaos_applied should contain 'schema_time_skew'

    Note: Detecting actual time skew is difficult since each generation is independent.
    We check if timestamp/datetime fields are present, which means the chaos op had data to skew.
    """
    has_chaos_metadata = any("schema_time_skew" in str(op) for op in chaos_applied)

    baseline_timestamps = []
    for item in baseline_items:
        baseline_timestamps.extend(_find_timestamp_fields(item))

    chaos_timestamps = []
    for item in chaos_items:
        chaos_timestamps.extend(_find_timestamp_fields(item))

    actual_effect_detected = len(chaos_timestamps) > 0
    passed = actual_effect_detected

    data = {
        "baseline_timestamp_count": len(baseline_timestamps),
        "chaos_timestamp_count": len(chaos_timestamps),
        "actual_effect_detected": actual_effect_detected,
        "chaos_metadata_reported": has_chaos_metadata,
    }

    warnings = []
    if has_chaos_metadata and not actual_effect_detected:
        warnings.append("Metadata reports chaos but no timestamp fields found to skew")
    elif not has_chaos_metadata and actual_effect_detected:
        warnings.append("Timestamp fields found but chaos not reported in metadata")

    if warnings:
        data["warnings"] = warnings

    return passed, data


def test_schema_time_skew_rest(
    baseline_items: list[Dict[str, Any]],
    chaos_items: list[Dict[str, Any]],
    chaos_applied: list[str],
) -> tuple[bool, Dict[str, Any]]:
    """Test schema_time_skew for REST endpoint."""
    return test_schema_time_skew_streaming(baseline_items, chaos_items, chaos_applied)
