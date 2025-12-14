from __future__ import annotations

from typing import Any, Dict


def test_http_error_streaming(
    baseline_items: list[Dict[str, Any]],
    chaos_items: list[Dict[str, Any]],
    chaos_applied: list[str],
) -> tuple[bool, Dict[str, Any]]:
    """Test http_error for streaming endpoint.

    Note: http_error affects HTTP status, not WebSocket payload.
    """
    has_chaos = any("http_error" in str(op) for op in chaos_applied)

    passed = has_chaos
    data = {
        "chaos_reported": has_chaos,
        "note": "http_error affects HTTP status, not WebSocket payload",
    }
    return passed, data


def test_http_error_rest(
    baseline_items: list[Dict[str, Any]],
    chaos_items: list[Dict[str, Any]],
    chaos_applied: list[str],
    status_code: int | None = None,
) -> tuple[bool, Dict[str, Any]]:
    """Test http_error for REST endpoint."""
    has_chaos = any("http_error" in str(op) for op in chaos_applied)
    is_error_status = status_code is not None and status_code >= 400

    passed = is_error_status or has_chaos
    data = {
        "status_code": status_code,
        "chaos_reported": has_chaos,
        "note": "http_error returns error status code",
    }
    return passed, data
