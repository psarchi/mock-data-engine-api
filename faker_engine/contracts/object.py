from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Mapping


@dataclass
class ObjectGeneratorSpec:
    """Object Generator Spec."""
    fields: Mapping[str, Any] | None = None
