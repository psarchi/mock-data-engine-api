from __future__ import annotations

from typing import Any, Dict


def test_latency_streaming(
    baseline_items: list[Dict[str, Any]],
    chaos_items: list[Dict[str, Any]],
    chaos_applied: list[str],
    baseline_elapsed: float | None = None,
    chaos_elapsed: float | None = None,
) -> tuple[bool, Dict[str, Any]]:
    """Test latency for streaming endpoint.

    PRIMARY: Actual effect - response time should increase by >20%
    BONUS: Metadata reporting - chaos_applied should contain 'latency'
    """
    has_chaos_metadata = any("latency" in str(op) for op in chaos_applied)

    if baseline_elapsed and chaos_elapsed:
        slowdown_ratio = chaos_elapsed / baseline_elapsed
        actual_effect_detected = chaos_elapsed > baseline_elapsed * 1.2
        passed = actual_effect_detected
    else:
        passed = False
        slowdown_ratio = None
        actual_effect_detected = None

    data = {
        "baseline_elapsed": baseline_elapsed,
        "chaos_elapsed": chaos_elapsed,
        "slowdown_ratio": slowdown_ratio,
        "actual_effect_detected": actual_effect_detected,
        "chaos_metadata_reported": has_chaos_metadata,
    }

    warnings = []
    if baseline_elapsed and chaos_elapsed:
        if has_chaos_metadata and not actual_effect_detected:
            warnings.append(
                "Metadata reports chaos but no actual latency increase detected"
            )
        elif not has_chaos_metadata and actual_effect_detected:
            warnings.append(
                "Actual latency increase detected but not reported in metadata"
            )

    if warnings:
        data["warnings"] = warnings

    return passed, data


def test_latency_rest(
    baseline_items: list[Dict[str, Any]],
    chaos_items: list[Dict[str, Any]],
    chaos_applied: list[str],
    baseline_elapsed: float | None = None,
    chaos_elapsed: float | None = None,
) -> tuple[bool, Dict[str, Any]]:
    """Test latency for REST endpoint."""
    return test_latency_streaming(
        baseline_items, chaos_items, chaos_applied, baseline_elapsed, chaos_elapsed
    )
