from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Optional, Union, Sequence, Mapping
from datetime import date, datetime, timezone


@dataclass
class ArrayGeneratorSpec:
    min_items: Optional[int] = None
    max_items: Optional[int] = None
    child: Any = None
