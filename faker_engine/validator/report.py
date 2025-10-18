from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, Tuple, List
from .errors import Issue

@dataclass
class Report:
    ok: bool
    issues: list[Issue] = field(default_factory=list)
    normalized: dict[str, Any] | None = None

    def by_path(self) -> Dict[Tuple[str | int, ...], List[Issue]]:
        buckets: Dict[Tuple[str | int, ...], List[Issue]] = {}
        for i in self.issues:
            buckets.setdefault(i.path, []).append(i)
        return buckets
