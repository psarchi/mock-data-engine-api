from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class ObjectOrNullGeneratorSpec:
    """Object Or Null Generator Spec."""
    child: Any = None
    p_null: Optional[float | int] = None
