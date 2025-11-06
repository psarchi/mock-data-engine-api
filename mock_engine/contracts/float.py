from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

@dataclass
class FloatGeneratorSpec:
    """Float Generator Spec."""
    min: Optional[float] = None
    max: Optional[float] = None
    precision: Optional[int] = None