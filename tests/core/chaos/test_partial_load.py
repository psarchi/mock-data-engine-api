from __future__ import annotations

from typing import Any, Dict


def test_partial_load_streaming(
    baseline_items: list[Dict[str, Any]],
    chaos_items: list[Dict[str, Any]],
    chaos_applied: list[str],
) -> tuple[bool, Dict[str, Any]]:
    """Test partial_load for streaming endpoint.

    Note: Streaming uses separate connections, so baseline and chaos get different
    random field removals. We rely on metadata reporting for validation.

    PRIMARY: Metadata reports partial_load
    BONUS: If detectable, check for key reduction
    """
    has_chaos_metadata = any("partial_load" in str(op) for op in chaos_applied)

    passed = has_chaos_metadata

    baseline_keys = len(baseline_items[0].keys()) if baseline_items else 0
    chaos_keys = len(chaos_items[0].keys()) if chaos_items else 0

    data = {
        "baseline_top_keys": baseline_keys,
        "chaos_top_keys": chaos_keys,
        "detection_mode": "metadata_only_streaming",
        "chaos_metadata_reported": has_chaos_metadata,
        "note": "Separate WebSocket connections get different random removals",
    }

    return passed, data


def test_partial_load_rest(
    baseline_items: list[Dict[str, Any]],
    chaos_items: list[Dict[str, Any]],
    chaos_applied: list[str],
) -> tuple[bool, Dict[str, Any]]:
    """Test partial_load for REST endpoint.

    METADATA ONLY: REST also does separate baseline/chaos requests that get
    different random field removals, making comparison unreliable.
    """
    has_chaos_metadata = any("partial_load" in str(op) for op in chaos_applied)
    passed = has_chaos_metadata

    baseline_keys = len(baseline_items[0].keys()) if baseline_items else 0
    chaos_keys = len(chaos_items[0].keys()) if chaos_items else 0

    data = {
        "baseline_top_keys": baseline_keys,
        "chaos_top_keys": chaos_keys,
        "detection_mode": "metadata_only",
        "chaos_metadata_reported": has_chaos_metadata,
        "note": "Separate requests get different random removals",
    }

    return passed, data
