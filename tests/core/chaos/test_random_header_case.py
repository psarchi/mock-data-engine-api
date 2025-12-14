from __future__ import annotations

from typing import Any, Dict


def test_random_header_case_streaming(
    baseline_items: list[Dict[str, Any]],
    chaos_items: list[Dict[str, Any]],
    chaos_applied: list[str],
) -> tuple[bool, Dict[str, Any]]:
    """Test random_header_case for streaming endpoint."""
    has_chaos = any("random_header_case" in str(op) for op in chaos_applied)

    passed = has_chaos
    data = {
        "chaos_reported": has_chaos,
        "note": "random_header_case affects HTTP headers, not WebSocket payload",
    }
    return passed, data


def test_random_header_case_rest(
    baseline_items: list[Dict[str, Any]],
    chaos_items: list[Dict[str, Any]],
    chaos_applied: list[str],
) -> tuple[bool, Dict[str, Any]]:
    """Test random_header_case for REST endpoint."""
    return test_random_header_case_streaming(baseline_items, chaos_items, chaos_applied)
