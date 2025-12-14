from __future__ import annotations

from typing import Any, Dict

from .utils import generate_from_schema


def test_bool_generator(
    count: int = 100, seed: int | None = None
) -> tuple[bool, Dict[str, Any]]:
    """Test bool generator.

    Returns:
        Tuple of (passed: bool, data: dict)
    """
    try:
        results = generate_from_schema("bool", count=count, seed=seed)

        if not results:
            return False, {"error": "No results generated"}

        values = [r["flag"] for r in results]
        all_bool = all(isinstance(v, bool) for v in values)
        has_true = any(v is True for v in values)
        has_false = any(v is False for v in values)

        passed = all_bool
        data = {
            "count": len(values),
            "all_bool": all_bool,
            "has_true": has_true,
            "has_false": has_false,
        }

        return passed, data
    except Exception as e:
        return False, {"error": str(e)}
