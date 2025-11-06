from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Optional, Sequence

@dataclass
class EnumGeneratorSpec:
    """Enum Generator Spec."""
    values: Optional[Sequence[Any]] = None
    weights: Optional[Sequence[float]] = None