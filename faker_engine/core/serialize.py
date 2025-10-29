from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import Any
from uuid import UUID

# Recursive JSON type aliases for clarity in signatures
JSONScalar = str | int | float | bool | None
JSONValue = JSONScalar | list["JSONValue"] | dict[str, "JSONValue"]

# TODO: probably move to a utils module
# TODO: unused
def to_jsonable(value: Any) -> JSONValue:
    """Convert ``value`` into a JSON-compatible form.

    The conversion is recursive for containers. Datetimes are rendered in ISO 8601
    via ``.isoformat()``; ``Decimal`` is cast to ``float``; ``UUID`` is cast to
    string. ``dict`` keys are coerced to ``str``.

    Args:
        value (Any): Input value to convert.

    Returns:
        JSONValue: A value that can be serialized by standard JSON encoders.

    Notes:
        - ``Decimal`` → ``float`` may introduce precision loss.
        - Non-string ``dict`` keys are stringified which may collide for keys with
          equal string representations.
    """
    if value is None:
        return None

    if isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, (datetime, date, time)):
        return value.isoformat()

    if isinstance(value, Decimal):
        # TODO(precision): consider returning string to preserve precision or make this configurable
        return float(value)

    if isinstance(value, UUID):
        return str(value)

    if isinstance(value, (list, tuple)):
        return [to_jsonable(item) for item in value]

    if isinstance(value, dict):
        # TODO(data): non-string keys are coerced to str; consider raising or preserving original keys elsewhere
        return {str(key): to_jsonable(item) for key, item in value.items()}

    # Fallback: let the object's string representation through
    return str(value)
