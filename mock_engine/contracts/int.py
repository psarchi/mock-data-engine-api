from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass
class IntGeneratorSpec:
    """Int Generator Spec."""
    min: Optional[int] = None
    max: Optional[int] = None
    step: Optional[int] = None
