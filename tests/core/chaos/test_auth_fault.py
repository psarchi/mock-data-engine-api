from __future__ import annotations

from typing import Any, Dict


def test_auth_fault_streaming(
    baseline_items: list[Dict[str, Any]],
    chaos_items: list[Dict[str, Any]],
    chaos_applied: list[str],
) -> tuple[bool, Dict[str, Any]]:
    """Test auth_fault for streaming endpoint.

    METADATA ONLY: auth_fault affects HTTP status codes, not accessible in WebSocket
    We can only check if chaos is reported in metadata.
    """
    has_chaos_metadata = any("auth_fault" in str(op) for op in chaos_applied)

    passed = has_chaos_metadata

    data = {
        "detection_mode": "metadata_only",
        "chaos_metadata_reported": has_chaos_metadata,
        "note": "auth_fault affects HTTP status (401/403), not accessible in WebSocket payload",
    }
    return passed, data


def test_auth_fault_rest(
    baseline_items: list[Dict[str, Any]],
    chaos_items: list[Dict[str, Any]],
    chaos_applied: list[str],
    status_code: int | None = None,
) -> tuple[bool, Dict[str, Any]]:
    """Test auth_fault for REST endpoint.

    PRIMARY: Actual effect - should return 401/403 HTTP status code
    BONUS: Metadata reporting - chaos_applied should contain 'auth_fault'

    Note: status_code must be passed by integration test fixture.
    """
    has_chaos_metadata = any("auth_fault" in str(op) for op in chaos_applied)

    actual_effect_detected = status_code in (401, 403) if status_code else False
    passed = actual_effect_detected

    data = {
        "status_code": status_code,
        "actual_effect_detected": actual_effect_detected,
        "chaos_metadata_reported": has_chaos_metadata,
    }

    warnings = []
    if has_chaos_metadata and not actual_effect_detected:
        warnings.append(
            f"Metadata reports chaos but status code is {status_code} (expected 401/403)"
        )
    elif not has_chaos_metadata and actual_effect_detected:
        warnings.append(
            f"Status code is {status_code} but chaos not reported in metadata"
        )

    if warnings:
        data["warnings"] = warnings

    return passed, data
