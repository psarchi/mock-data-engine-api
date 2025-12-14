from __future__ import annotations

from typing import Any, Dict

from .utils import generate_from_schema


def test_array_generator(
    count: int = 100, seed: int | None = None
) -> tuple[bool, Dict[str, Any]]:
    """Test array generator with bounds.

    Returns:
        Tuple of (passed: bool, data: dict)
    """
    try:
        results = generate_from_schema("array", count=count, seed=seed)

        if not results:
            return False, {"error": "No results generated"}

        arrays = [r["arr"] for r in results]
        all_arrays = all(isinstance(arr, list) for arr in arrays)

        lengths = [len(arr) for arr in arrays]
        all_in_bounds = all(1 <= length <= 3 for length in lengths)

        all_bool_children = all(
            all(isinstance(item, bool) for item in arr) for arr in arrays
        )

        passed = all_arrays and all_in_bounds and all_bool_children
        data = {
            "count": len(arrays),
            "all_arrays": all_arrays,
            "all_in_bounds": all_in_bounds,
            "all_bool_children": all_bool_children,
            "min_length": min(lengths) if lengths else 0,
            "max_length": max(lengths) if lengths else 0,
        }

        return passed, data
    except Exception as e:
        return False, {"error": str(e)}
