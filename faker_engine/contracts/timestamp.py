from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Optional, Union, Sequence, Mapping
from datetime import date, datetime, timezone


@dataclass
class TimestampGeneratorSpec:
    unit: Optional[str] = None
    start: Optional[Union[int, float, str, datetime]] = None
    end: Optional[Union[int, float, str, datetime]] = None
