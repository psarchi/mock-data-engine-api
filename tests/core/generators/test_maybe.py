from __future__ import annotations

from typing import Any, Dict

from .utils import generate_from_schema


def test_maybe_generator(
    count: int = 100, seed: int | None = None
) -> tuple[bool, Dict[str, Any]]:
    """Test maybe generator with null probability.

    Returns:
        Tuple of (passed: bool, data: dict)
    """
    try:
        results = generate_from_schema("maybe", count=count, seed=seed)

        if not results:
            return False, {"error": "No results generated"}

        always_null_values = [r["always_null"] for r in results]
        never_null_values = [r["never_null"] for r in results]

        all_null = all(v is None for v in always_null_values)

        all_not_null = all(v is not None for v in never_null_values)

        passed = all_null and all_not_null
        data = {
            "count": len(results),
            "all_null": all_null,
            "all_not_null": all_not_null,
            "always_null_count": sum(1 for v in always_null_values if v is None),
            "never_null_count": sum(1 for v in never_null_values if v is not None),
        }

        return passed, data
    except Exception as e:
        return False, {"error": str(e)}
