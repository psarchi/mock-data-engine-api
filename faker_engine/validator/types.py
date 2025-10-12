from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Literal, List, Optional


@dataclass(slots=True)
class Issue:
    level: Literal["error"]  # strict-only for now
    code: str
    path: str
    message: str
    hint: Optional[str] = None


@dataclass(slots=True)
class Report:
    errors: List[Issue]
    warnings: List[Issue]  # reserved


@dataclass(slots=True)
class Ctx:
    registry: Any | None = None
    version: str = "0"
