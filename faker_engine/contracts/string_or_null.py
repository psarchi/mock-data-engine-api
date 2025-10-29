from __future__ import annotations
from dataclasses import dataclass
from typing import Any


@dataclass
class StringOrNullGeneratorSpec:
    """String Or Null Generator Spec."""
    child: Any = None
    weights: Any = None
