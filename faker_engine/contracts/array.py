from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class ArrayGeneratorSpec:
    """Array Generator Spec."""
    min_items: Optional[int] = None
    max_items: Optional[int] = None
    child: Any = None
