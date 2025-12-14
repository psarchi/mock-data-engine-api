from __future__ import annotations

from typing import Any, Dict

from .utils import generate_from_schema


def test_one_of_generator(
    count: int = 100, seed: int | None = None
) -> tuple[bool, Dict[str, Any]]:
    """Test one_of generator with choices and weights.

    Returns:
        Tuple of (passed: bool, data: dict)
    """
    try:
        results = generate_from_schema("one_of", count=count, seed=seed)

        if not results:
            return False, {"error": "No results generated"}

        uniform_values = [r["choice_uniform"] for r in results]
        weighted_values = [r["choice_weighted"] for r in results]

        uniform_valid = all(v in ("A", "B") for v in uniform_values)
        weighted_valid = all(v in ("A", "B") for v in weighted_values)

        b_count = sum(1 for v in weighted_values if v == "B")
        a_count = sum(1 for v in weighted_values if v == "A")
        weighted_ok = b_count > a_count * 10

        passed = uniform_valid and weighted_valid
        data = {
            "count": len(results),
            "uniform_valid": uniform_valid,
            "weighted_valid": weighted_valid,
            "weighted_a_count": a_count,
            "weighted_b_count": b_count,
            "weighted_ok": weighted_ok,
        }

        return passed, data
    except Exception as e:
        return False, {"error": str(e)}
