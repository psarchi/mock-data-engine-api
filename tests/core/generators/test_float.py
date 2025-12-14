from __future__ import annotations

from typing import Any, Dict

from .utils import build_generator_from_schema


def test_float_generator(
    count: int = 100, seed: int | None = None
) -> tuple[bool, Dict[str, Any]]:
    """Test float generator.

    Returns:
        Tuple of (passed: bool, data: dict)
    """
    try:
        gen, ctx = build_generator_from_schema("numbers", seed=seed)
        results = [gen.generate(ctx) for _ in range(count)]

        if not results:
            return False, {"error": "No results generated"}

        has_float = any(isinstance(v, float) for r in results for v in r.values())

        passed = has_float
        data = {
            "count": len(results),
            "has_float": has_float,
        }

        return passed, data
    except Exception as e:
        return False, {"error": str(e)}
