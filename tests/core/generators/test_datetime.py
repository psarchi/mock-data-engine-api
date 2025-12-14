from __future__ import annotations

from typing import Any, Dict

from .utils import generate_from_schema


def test_datetime_generator(
    count: int = 100, seed: int | None = None
) -> tuple[bool, Dict[str, Any]]:
    """Test datetime generator with formats.

    Returns:
        Tuple of (passed: bool, data: dict)
    """
    try:
        results = generate_from_schema("time", count=count, seed=seed)

        if not results:
            return False, {"error": "No results generated"}

        date_iso_values = [r.get("date_iso") for r in results]
        datetime_iso_values = [r.get("datetime_iso") for r in results]

        date_format_ok = all(
            isinstance(d, str) and len(d) == 10 and d[4] == "-" and d[7] == "-"
            for d in date_iso_values
            if d is not None
        )

        datetime_format_ok = all(
            isinstance(dt, str) and "T" in dt
            for dt in datetime_iso_values
            if dt is not None
        )

        passed = date_format_ok and datetime_format_ok
        data = {
            "count": len(results),
            "date_format_ok": date_format_ok,
            "datetime_format_ok": datetime_format_ok,
            "sample_dates": date_iso_values[:3] if date_iso_values else [],
            "sample_datetimes": datetime_iso_values[:3] if datetime_iso_values else [],
        }

        return passed, data
    except Exception as e:
        return False, {"error": str(e)}
