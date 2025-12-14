from __future__ import annotations

import json
from typing import Any, Dict


def test_schema_bloat_streaming(
    baseline_items: list[Dict[str, Any]],
    chaos_items: list[Dict[str, Any]],
    chaos_applied: list[str],
) -> tuple[bool, Dict[str, Any]]:
    """Test schema_bloat for streaming endpoint.

    METADATA ONLY: Streaming uses separate connections that get different random
    cache data, making size comparison unreliable.
    """
    has_chaos_metadata = any("schema_bloat" in str(op) for op in chaos_applied)
    passed = has_chaos_metadata

    data = {
        "detection_mode": "metadata_only",
        "reason": "streaming_random_data",
        "chaos_metadata_reported": has_chaos_metadata,
        "note": "Separate connections get different cache data, size comparison unreliable",
    }
    return passed, data


def test_schema_bloat_rest(
    baseline_items: list[Dict[str, Any]],
    chaos_items: list[Dict[str, Any]],
    chaos_applied: list[str],
) -> tuple[bool, Dict[str, Any]]:
    """Test schema_bloat for REST endpoint.

    PRIMARY: Actual effect - chaos items should be larger (>1% increase)
    BONUS: Metadata reporting
    """
    baseline_sizes = [len(json.dumps(item)) for item in baseline_items]
    baseline_avg = sum(baseline_sizes) / len(baseline_sizes) if baseline_sizes else 0

    chaos_sizes = [len(json.dumps(item)) for item in chaos_items]
    chaos_avg = sum(chaos_sizes) / len(chaos_sizes) if chaos_sizes else 0

    has_chaos_metadata = any("schema_bloat" in str(op) for op in chaos_applied)

    actual_effect_detected = chaos_avg > baseline_avg * 1.01
    passed = actual_effect_detected

    bloat_ratio = chaos_avg / baseline_avg if baseline_avg > 0 else None
    increase_pct = ((chaos_avg / baseline_avg) - 1) * 100 if baseline_avg > 0 else None

    data = {
        "baseline_avg_size": baseline_avg,
        "chaos_avg_size": chaos_avg,
        "bloat_ratio": bloat_ratio,
        "increase_pct": increase_pct,
        "actual_effect_detected": actual_effect_detected,
        "chaos_metadata_reported": has_chaos_metadata,
    }

    warnings = []
    if has_chaos_metadata and not actual_effect_detected:
        warnings.append(
            f"Metadata reports chaos but increase is only {increase_pct:.2f}%"
        )
    elif not has_chaos_metadata and actual_effect_detected:
        warnings.append("Size increase detected but not reported in metadata")

    if warnings:
        data["warnings"] = warnings

    return passed, data
