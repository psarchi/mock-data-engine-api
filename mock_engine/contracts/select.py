from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Optional, Mapping


@dataclass
class SelectGeneratorSpec:
    """Select Generator Spec."""
    options: Mapping[str, Any] | None = None
    pick: Optional[int] = None
