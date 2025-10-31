"""Validator report types.

Defines the :class:`Report` data class used by the validator to return
normalization results and structured issues.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from faker_engine.validator.errors import Issue


@dataclass
class Report:
    """Validation report with overall status, issues, and normalized output.

    Attributes:
        ok (bool): Overall validation status.
        issues (list[Issue]): Collected issues discovered during validation.
        normalized (dict[str, Any] | None): Normalized payload when available.
    """

    ok: bool
    issues: list[Issue] = field(default_factory=list)
    normalized: dict[str, Any] | None = None

    def by_path(self) -> dict[tuple[str | int, ...], list[Issue]]:
        """Group issues by their ``path``.

        Returns:
            dict[tuple[str | int, ...], list[Issue]]: Mapping from path tuples to
                lists of issues under that path.
        """
        issues_by_path: dict[tuple[str | int, ...], list[Issue]] = {}
        for issue in self.issues:
            issues_by_path.setdefault(issue.path, []).append(issue)
        return issues_by_path

    def pretty(self) -> str:
        """Return a human-readable summary of this report.

        Returns:
            str: ``"OK (0 issues)"`` when ``ok`` is ``True``; otherwise a multi-line
                string enumerating issues with index, code, path, and message.
        """
        if self.ok:
            return "OK (0 issues)"

        lines: list[str] = [f"FAIL ({len(self.issues)} issues)"]
        for index, issue in enumerate(self.issues, start=1):
            path_text = (
                ".".join(str(segment) for segment in issue.path)
                if getattr(issue, "path", None)
                else "<root>"
            )
            lines.append(f"{index:02d}. [{issue.code}] {path_text} — {issue.msg}")
        return "".join(lines)
