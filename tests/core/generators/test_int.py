from __future__ import annotations

from typing import Any, Dict

from .utils import generate_from_schema


def test_int_generator(
    count: int = 100, seed: int | None = None
) -> tuple[bool, Dict[str, Any]]:
    """Test int generator with bounds.

    Returns:
        Tuple of (passed: bool, data: dict)
    """
    try:
        results = generate_from_schema("int", count=count, seed=seed)

        if not results:
            return False, {"error": "No results generated"}

        values = [r["num"] for r in results]
        min_val = min(values)
        max_val = max(values)

        all_in_bounds = all(1 <= v <= 5 for v in values)

        passed = all_in_bounds
        data = {
            "count": len(values),
            "min": min_val,
            "max": max_val,
            "all_in_bounds": all_in_bounds,
        }

        return passed, data
    except Exception as e:
        return False, {"error": str(e)}
