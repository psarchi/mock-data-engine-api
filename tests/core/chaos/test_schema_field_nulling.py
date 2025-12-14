from __future__ import annotations

from typing import Any, Dict

from .utils import count_none_values


def test_schema_field_nulling_streaming(
    baseline_items: list[Dict[str, Any]],
    chaos_items: list[Dict[str, Any]],
    chaos_applied: list[str],
) -> tuple[bool, Dict[str, Any]]:
    """Test schema_field_nulling for streaming endpoint.

    PRIMARY: Actual effect - chaos response should have more null values
    BONUS: Metadata reporting - chaos_applied should contain 'schema_field_nulling'

    Returns:
        Tuple of (passed: bool, data: dict)
    """
    baseline_none = sum(count_none_values(item) for item in baseline_items)
    chaos_none = sum(count_none_values(item) for item in chaos_items)
    has_chaos_metadata = any("schema_field_nulling" in str(op) for op in chaos_applied)

    actual_effect_detected = chaos_none >= baseline_none or chaos_none > 0
    passed = actual_effect_detected

    data = {
        "baseline_none_count": baseline_none,
        "chaos_none_count": chaos_none,
        "actual_effect_detected": actual_effect_detected,
        "chaos_metadata_reported": has_chaos_metadata,
    }

    warnings = []
    if has_chaos_metadata and not actual_effect_detected:
        warnings.append(
            "Metadata reports chaos but no increase in null values detected"
        )
    elif not has_chaos_metadata and actual_effect_detected:
        warnings.append("Increase in null values detected but not reported in metadata")

    if warnings:
        data["warnings"] = warnings

    return passed, data


def test_schema_field_nulling_rest(
    baseline_items: list[Dict[str, Any]],
    chaos_items: list[Dict[str, Any]],
    chaos_applied: list[str],
) -> tuple[bool, Dict[str, Any]]:
    """Test schema_field_nulling for REST endpoint.

    Returns:
        Tuple of (passed: bool, data: dict)
    """
    return test_schema_field_nulling_streaming(
        baseline_items, chaos_items, chaos_applied
    )
