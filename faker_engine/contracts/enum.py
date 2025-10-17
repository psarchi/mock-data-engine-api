from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Optional, Union, Sequence, Mapping
from datetime import date, datetime, timezone


@dataclass
class EnumGeneratorSpec:
    values: Optional[Sequence[Any]] = None
    weights: Optional[Sequence[float]] = None
