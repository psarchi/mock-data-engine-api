from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Optional, Union, Sequence, Mapping
from datetime import date, datetime, timezone


@dataclass
class FloatGeneratorSpec:
    min: Optional[float] = None
    max: Optional[float] = None
    precision: Optional[int] = None
