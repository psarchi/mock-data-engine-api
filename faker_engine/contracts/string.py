from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Optional, Union, Sequence, Mapping, Literal
from datetime import date, datetime, timezone


@dataclass
class StringGeneratorSpec:
    string_type: Optional[str] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    regex: Optional[str] = None
    template: Optional[str] = None
    charset: Optional[Sequence[str]] = None
    n_type: Optional[str] = None
    n_charset: Optional[Sequence[str]] = None
