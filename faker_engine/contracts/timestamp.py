from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Union
from datetime import datetime


@dataclass
class TimestampGeneratorSpec:
    """Timestamp Generator Spec."""
    unit: Optional[str] = None
    start: Optional[Union[int, float, str, datetime]] = None
    end: Optional[Union[int, float, str, datetime]] = None
