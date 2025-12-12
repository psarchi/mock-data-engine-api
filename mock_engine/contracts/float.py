from __future__ import annotations
from typing import Optional, ClassVar, Set
from pydantic import BaseModel, ConfigDict


class FloatGeneratorSpec(BaseModel):
    """Float Generator Spec."""

    # type aliasing
    type_token: ClassVar[str] = "float"
    type_aliases: ClassVar[Set[str]] = ["double", "number"]
    model_config = ConfigDict(extra="forbid")

    min: Optional[float] = None
    max: Optional[float] = None
    precision: Optional[int] = None
