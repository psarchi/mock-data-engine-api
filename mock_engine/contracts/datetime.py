from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Union
from datetime import datetime


@dataclass
class DateTimeGeneratorSpec:
    """Date Time Generator Spec."""
    start: Optional[Union[int, float, str, datetime]] = None
    end: Optional[Union[int, float, str, datetime]] = None
    format: Optional[str] = None
    time_start: Optional[str] = None
    time_end: Optional[str] = None
    tz: Optional[str] = None
