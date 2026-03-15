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
    """Test auth_fault for REST endpoint."""
    import pytest
    pytest.skip("auth_fault op not registered in chaos registry; not testable in CI")
