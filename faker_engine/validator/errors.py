from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Any, Tuple, List


class IssueCode(str, Enum):
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
    code: IssueCode
    path: Tuple[str | int, ...]
    msg: str
    detail: dict[str, Any] | None = None


@dataclass
class RequiredIssue(Issue):
    code: IssueCode = IssueCode.REQUIRED


@dataclass
class ExtraIssue(Issue):
    code: IssueCode = IssueCode.EXTRA


@dataclass
class TypeIssue(Issue):
    code: IssueCode = IssueCode.TYPE


@dataclass
class RangeIssue(Issue):
    code: IssueCode = IssueCode.RANGE


@dataclass
class RegexIssue(Issue):
    code: IssueCode = IssueCode.REGEX


@dataclass
class EnumIssue(Issue):
    code: IssueCode = IssueCode.ENUM


# Mapper from Pydantic v2 error dicts
def _to_path(loc: List[Any]) -> Tuple[str | int, ...]:
    return tuple(loc) if isinstance(loc, list) else tuple([loc])


def from_pydantic_errors(errors: List[dict[str, Any]]) -> list[Issue]:
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
        elif any(k in t for k in (
                "too_short", "too_long", "greater_than", "less_than", "ge",
                "le", "gt",
                "lt")):
            out.append(RangeIssue(path=loc, msg=msg, detail=ctx))
        elif "pattern" in t or "regex" in t:
            out.append(RegexIssue(path=loc, msg=msg, detail=ctx))
        elif "enum" in t or "literal" in t:
            out.append(EnumIssue(path=loc, msg=msg, detail=ctx))
        else:
            out.append(Issue(code=IssueCode.TYPE, path=loc, msg=msg,
                             detail={"raw": e}))  # default
    return out


class ValidationFailed(Exception):
    def __init__(self, report):
        self.report = report
        super().__init__(getattr(report, 'pretty', lambda: str(report))())
