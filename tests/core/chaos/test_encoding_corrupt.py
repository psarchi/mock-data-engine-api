from __future__ import annotations

from typing import Any, Dict

from .utils import has_corrupted_encoding


def test_encoding_corrupt_streaming(
    baseline_items: list[Dict[str, Any]],
    chaos_items: list[Dict[str, Any]],
    chaos_applied: list[str],
) -> tuple[bool, Dict[str, Any]]:
    """Test encoding_corrupt for streaming endpoint."""
    baseline_corrupted = any(has_corrupted_encoding(item) for item in baseline_items)
    chaos_corrupted = any(has_corrupted_encoding(item) for item in chaos_items)
    has_chaos = any("encoding_corrupt" in str(op) for op in chaos_applied)

    passed = chaos_corrupted or has_chaos
    data = {
        "baseline_corrupted": baseline_corrupted,
        "chaos_corrupted": chaos_corrupted,
        "chaos_reported": has_chaos,
    }
    return passed, data


def test_encoding_corrupt_rest(
    baseline_items: list[Dict[str, Any]],
    chaos_items: list[Dict[str, Any]],
    chaos_applied: list[str],
) -> tuple[bool, Dict[str, Any]]:
    """Test encoding_corrupt for REST endpoint."""
    return test_encoding_corrupt_streaming(baseline_items, chaos_items, chaos_applied)
