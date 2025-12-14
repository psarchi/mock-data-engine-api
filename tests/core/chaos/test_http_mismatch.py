from __future__ import annotations

from typing import Any, Dict


def test_http_mismatch_streaming(
    baseline_items: list[Dict[str, Any]],
    chaos_items: list[Dict[str, Any]],
    chaos_applied: list[str],
) -> tuple[bool, Dict[str, Any]]:
    """Test http_mismatch for streaming endpoint."""
    has_chaos = any("http_mismatch" in str(op) for op in chaos_applied)

    passed = has_chaos
    data = {
        "chaos_reported": has_chaos,
        "note": "http_mismatch affects HTTP status, not WebSocket payload",
    }
    return passed, data


def test_http_mismatch_rest(
    baseline_items: list[Dict[str, Any]],
    chaos_items: list[Dict[str, Any]],
    chaos_applied: list[str],
    status_code: int | None = None,
) -> tuple[bool, Dict[str, Any]]:
    """Test http_mismatch for REST endpoint."""
    has_chaos = any("http_mismatch" in str(op) for op in chaos_applied)
    is_error_status = status_code is not None and status_code >= 400

    passed = has_chaos or is_error_status
    data = {
        "status_code": status_code,
        "chaos_reported": has_chaos,
        "note": "http_mismatch affects HTTP status",
    }
    return passed, data
