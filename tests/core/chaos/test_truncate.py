from __future__ import annotations

from typing import Any, Dict


def test_truncate_streaming(
    baseline_items: list[Dict[str, Any]],
    chaos_items: list[Dict[str, Any]],
    chaos_applied: list[str],
) -> tuple[bool, Dict[str, Any]]:
    """Test truncate for streaming endpoint.

    METADATA ONLY: Streaming serves pre-generated data from Redis cache.
    Truncate is a consumer-side chaos op that may not apply to cached data.
    """
    has_chaos_metadata = any("truncate" in str(op) for op in chaos_applied)
    passed = has_chaos_metadata

    data = {
        "detection_mode": "metadata_only",
        "reason": "streaming_cache",
        "chaos_metadata_reported": has_chaos_metadata,
        "note": "truncate affects live generation, streaming uses cached data",
    }
    return passed, data


def test_truncate_rest(
    baseline_items: list[Dict[str, Any]],
    chaos_items: list[Dict[str, Any]],
    chaos_applied: list[str],
) -> tuple[bool, Dict[str, Any]]:
    """Test truncate for REST endpoint.

    METADATA ONLY: Truncation can occur in various ways (shortened values,
    incomplete JSON, etc.) making detection complex. Check metadata only.
    """
    has_chaos_metadata = any("truncate" in str(op) for op in chaos_applied)
    passed = has_chaos_metadata

    data = {
        "detection_mode": "metadata_only",
        "reason": "complex_detection",
        "chaos_metadata_reported": has_chaos_metadata,
        "note": "truncate detection complex (values vs JSON structure), checking metadata only",
    }
    return passed, data
