from __future__ import annotations

from typing import Any, Dict

from .utils import generate_from_schema


def test_object_generator(
    count: int = 100, seed: int | None = None
) -> tuple[bool, Dict[str, Any]]:
    """Test object generator with nested fields.

    Returns:
        Tuple of (passed: bool, data: dict)
    """
    try:
        results = generate_from_schema("object_basic", count=count, seed=seed)

        if not results:
            return False, {"error": "No results generated"}

        all_objects = all(isinstance(r, dict) for r in results)

        nested_ok = True
        for r in results:
            if "obj" not in r:
                nested_ok = False
                break
            obj = r["obj"]
            if not isinstance(obj, dict):
                nested_ok = False
                break
            if "id" not in obj or "ok" not in obj or "label" not in obj:
                nested_ok = False
                break

        passed = all_objects and nested_ok
        data = {
            "count": len(results),
            "all_objects": all_objects,
            "nested_ok": nested_ok,
        }

        return passed, data
    except Exception as e:
        return False, {"error": str(e)}
