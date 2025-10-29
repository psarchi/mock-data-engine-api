from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Sequence


@dataclass
class OneOfGeneratorSpec:
    """One Of Generator Spec."""
    choices: Sequence[Any] | None = None
    weights: Sequence[float] | None = None
