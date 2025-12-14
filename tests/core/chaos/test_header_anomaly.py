from __future__ import annotations

from typing import Any, Dict


def test_header_anomaly_streaming(
    baseline_items: list[Dict[str, Any]],
    chaos_items: list[Dict[str, Any]],
    chaos_applied: list[str],
) -> tuple[bool, Dict[str, Any]]:
    """Test header_anomaly for streaming endpoint.

    SKIP: header_anomaly affects HTTP headers only, cannot be detected in payload.
    This op has been removed from registry and is not testable via payload inspection.
    """
    passed = True

    data = {
        "detection_mode": "skip",
        "reason": "http_headers_only",
        "note": "header_anomaly affects HTTP headers, not accessible in WebSocket/REST payload",
    }
    return passed, data


def test_header_anomaly_rest(
    baseline_items: list[Dict[str, Any]],
    chaos_items: list[Dict[str, Any]],
    chaos_applied: list[str],
) -> tuple[bool, Dict[str, Any]]:
    """Test header_anomaly for REST endpoint.

    SKIP: header_anomaly affects HTTP headers only, cannot be detected in payload.
    This op has been removed from registry and is not testable via payload inspection.
    """
    return test_header_anomaly_streaming(baseline_items, chaos_items, chaos_applied)
