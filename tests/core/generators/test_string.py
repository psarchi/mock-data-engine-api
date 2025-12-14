from __future__ import annotations

from typing import Any, Dict

from .utils import generate_from_schema


def test_string_generator(
    count: int = 100, seed: int | None = None
) -> tuple[bool, Dict[str, Any]]:
    """Test string generator with templates, regex, faker.

    Returns:
        Tuple of (passed: bool, data: dict)
    """
    try:
        results = generate_from_schema("string", count=count, seed=seed)

        if not results:
            return False, {"error": "No results generated"}

        all_strings = True
        template_upper_ok = False
        template_numeric_ok = False
        regex_ok = False
        faker_ok = False

        for r in results:
            for key, value in r.items():
                if not isinstance(value, str):
                    all_strings = False
                    continue

                if key == "template_upper" and value.startswith("ISO-"):
                    template_upper_ok = True
                elif key == "template_numeric" and value.startswith("ID-"):
                    template_numeric_ok = True
                elif key == "regex_plain" and len(value) >= 8:
                    regex_ok = True
                elif key == "faker_name":
                    faker_ok = True

        passed = all_strings
        data = {
            "count": len(results),
            "all_strings": all_strings,
            "template_upper_ok": template_upper_ok,
            "template_numeric_ok": template_numeric_ok,
            "regex_ok": regex_ok,
            "faker_ok": faker_ok,
        }

        return passed, data
    except Exception as e:
        return False, {"error": str(e)}
