from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Sequence


@dataclass
class StringGeneratorSpec:
    """String Generator Spec."""
    string_type: Optional[str] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    regex: Optional[str] = None
    template: Optional[str] = None
    charset: Optional[Sequence[str]] = None
    n_type: Optional[str] = None
    n_charset: Optional[Sequence[str]] = None
