from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass
class BoolGeneratorSpec:
    """Bool Generator Spec."""
    p_true: Optional[float | int] = None
