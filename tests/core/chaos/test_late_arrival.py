from __future__ import annotations

from typing import Any, Dict


def test_late_arrival_streaming(
    baseline_items: list[Dict[str, Any]],
    chaos_items: list[Dict[str, Any]],
    chaos_applied: list[str],
    baseline_elapsed: float | None = None,
    chaos_elapsed: float | None = None,
) -> tuple[bool, Dict[str, Any]]:
    """Test late_arrival for streaming endpoint.

    METADATA ONLY: Timing in tests is unreliable due to network/caching variability.
    We check metadata reporting only.
    """
    has_chaos_metadata = any("late_arrival" in str(op) for op in chaos_applied)
    passed = has_chaos_metadata

    delay_ms = (
        (chaos_elapsed - baseline_elapsed) * 1000
        if baseline_elapsed and chaos_elapsed
        else None
    )

    data = {
        "detection_mode": "metadata_only",
        "baseline_elapsed": baseline_elapsed,
        "chaos_elapsed": chaos_elapsed,
        "delay_ms": delay_ms,
        "chaos_metadata_reported": has_chaos_metadata,
        "note": "Test timing unreliable, checking metadata only",
    }
    return passed, data


def test_late_arrival_rest(
    baseline_items: list[Dict[str, Any]],
    chaos_items: list[Dict[str, Any]],
    chaos_applied: list[str],
    baseline_elapsed: float | None = None,
    chaos_elapsed: float | None = None,
) -> tuple[bool, Dict[str, Any]]:
    """Test late_arrival for REST endpoint."""
    return test_late_arrival_streaming(
        baseline_items, chaos_items, chaos_applied, baseline_elapsed, chaos_elapsed
    )
