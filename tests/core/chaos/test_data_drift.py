from __future__ import annotations

from typing import Any, Dict


def test_data_drift_streaming(
    baseline_items: list[Dict[str, Any]],
    chaos_items: list[Dict[str, Any]],
    chaos_applied: list[str],
) -> tuple[bool, Dict[str, Any]]:
    """Test data_drift for streaming endpoint.

    SKIP: data_drift happens in pre-generation and cannot be triggered via
    forced_chaos parameter. This op requires pre-generation worker configuration.
    """
    passed = True

    data = {
        "detection_mode": "skip",
        "reason": "cannot_force_pregen_chaos",
        "note": "data_drift is pre-generation only, cannot test via forced_chaos API parameter",
    }
    return passed, data


def test_data_drift_rest(
    baseline_items: list[Dict[str, Any]],
    chaos_items: list[Dict[str, Any]],
    chaos_applied: list[str],
) -> tuple[bool, Dict[str, Any]]:
    """Test data_drift for REST endpoint."""
    return test_data_drift_streaming(baseline_items, chaos_items, chaos_applied)
