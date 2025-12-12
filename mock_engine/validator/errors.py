from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class IssueCode(str, Enum):
    """Issue Code."""

    REQUIRED = "REQUIRED"
    EXTRA = "EXTRA"
    TYPE = "TYPE"
    RANGE = "RANGE"
    REGEX = "REGEX"
    ENUM = "ENUM"
    ALIAS = "ALIAS"
    DEPRECATION = "DEPRECATION"
    RULE = "RULE"


@dataclass
class Issue:
    """Issue."""

    code: IssueCode
    path: tuple[str | int, ...]
    msg: str
    detail: dict[str, Any] | None = None


@dataclass
class RequiredIssue(Issue):
    """Required Issue."""

    code: IssueCode = field(default=IssueCode.REQUIRED, init=False)


@dataclass
class ExtraIssue(Issue):
    """Extra Issue."""

    code: IssueCode = field(default=IssueCode.EXTRA, init=False)


@dataclass
class TypeIssue(Issue):
    """Type Issue."""

    code: IssueCode = field(default=IssueCode.TYPE, init=False)


@dataclass
class RangeIssue(Issue):
    """Range Issue."""

    code: IssueCode = field(default=IssueCode.RANGE, init=False)


@dataclass
class RegexIssue(Issue):
    """Regex Issue."""

    code: IssueCode = field(default=IssueCode.REGEX, init=False)


@dataclass
class EnumIssue(Issue):
    """Enum Issue."""

    code: IssueCode = field(default=IssueCode.ENUM, init=False)


def _to_path(loc: list[Any]) -> tuple[str | int, ...]:
    """To path.

    Args:
        loc (list[Any]): Value.

    Returns:
        tuple[str | int, ...]: Value."""
    return tuple(loc) if isinstance(loc, list) else tuple([loc])


def from_pydantic_errors(errors: list[dict[str, Any]]) -> list[Issue]:
    """From pydantic_errors.

    Args:
        errors (list[dict[str, Any]]): Value.

    Returns:
        list[Issue]: List of values."""
    out: list[Issue] = []
    for e in errors:
        t = e.get("type", "")
        loc = _to_path(e.get("loc", []))
        msg = e.get("msg", t)
        ctx = e.get("ctx") or {}
        if t in ("missing", "value_error.missing"):
            out.append(RequiredIssue(path=loc, msg=msg, detail=ctx))
        elif t in ("extra_forbidden", "value_error.extra"):
            out.append(ExtraIssue(path=loc, msg=msg, detail=ctx))
        elif t.startswith("type_") or "type_error" in t:
            out.append(TypeIssue(path=loc, msg=msg, detail=ctx))
        elif any(
            (
                k in t
                for k in (
                    "too_short",
                    "too_long",
                    "greater_than",
                    "less_than",
                    "ge",
                    "le",
                    "gt",
                    "lt",
                )
            )
        ):
            out.append(RangeIssue(path=loc, msg=msg, detail=ctx))
        elif "pattern" in t or "regex" in t:
            out.append(RegexIssue(path=loc, msg=msg, detail=ctx))
        elif "enum" in t or "literal" in t:
            out.append(EnumIssue(path=loc, msg=msg, detail=ctx))
        else:
            out.append(Issue(code=IssueCode.TYPE, path=loc, msg=msg, detail={"raw": e}))
    return out


class ValidationFailed(Exception):
    """Validation Failed."""

    def __init__(self: object, report: object) -> None:
        """Init _.

        Args:
            report (object): Value.

        Returns:
            None: Value."""
        self.report = report
        super().__init__(getattr(report, "pretty", lambda: str(report))())
