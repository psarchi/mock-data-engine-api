from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Optional, Union, Sequence, Mapping
from datetime import date, datetime, timezone


@dataclass
class DateGeneratorSpec:
    start: Optional[Union[date, str]] = None
    end: Optional[Union[date, str]] = None
    format: Optional[str] = None
