from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Optional, Union, Sequence, Mapping
from datetime import date, datetime, timezone


@dataclass
class ObjectOrNullGeneratorSpec:
    child: Any = None
    p_null: Optional[float | int] = None
