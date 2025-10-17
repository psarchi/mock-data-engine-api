from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Optional, Union, Sequence, Mapping
from datetime import date, datetime, timezone


@dataclass
class OneOfGeneratorSpec:
    choices: Sequence[Any] | None = None
    weights: Sequence[float] | None = None
