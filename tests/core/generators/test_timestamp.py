from __future__ import annotations

from typing import Any, Dict

from .utils import generate_from_schema


def test_timestamp_generator(
    count: int = 100, seed: int | None = None
) -> tuple[bool, Dict[str, Any]]:
    """Test timestamp generator.

    Returns:
        Tuple of (passed: bool, data: dict)
    """
    try:
        results = generate_from_schema("time", count=count, seed=seed)

        if not results:
            return False, {"error": "No results generated"}

        timestamps = [r.get("timestamp_us") for r in results]
        all_timestamps = all(
            isinstance(ts, (int, float)) for ts in timestamps if ts is not None
        )

        all_positive = all(ts > 0 for ts in timestamps if ts is not None)

        passed = all_timestamps and all_positive
        data = {
            "count": len(results),
            "all_timestamps": all_timestamps,
            "all_positive": all_positive,
            "sample_values": timestamps[:3] if timestamps else [],
        }

        return passed, data
    except Exception as e:
        return False, {"error": str(e)}
