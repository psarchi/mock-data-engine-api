from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, Tuple, List
from faker_engine.validator.errors import Issue


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


def pretty(self) -> str:
    if self.ok:
        return "OK (0 issues)"
    lines = ["FAIL ({} issues)".format(len(self.issues))]
    for i, issue in enumerate(self.issues, 1):
        p = ".".join(str(x) for x in issue.path) if getattr(issue, "path",
                                                            None) else "<root>"
        lines.append(f"{i:02d}. [{issue.code}] {p} — {issue.msg}")
    return "\n".join(lines)
