"""Validation API routes.

Exposes ``POST /v1/validate`` to validate an input spec and return a report.
Behavior preserved; docstrings and typing follow the golden style.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from server.deps import get_validator
from server.models import Issue as IssueModel
from server.models import ValidateRequest, ValidateResponse

router = APIRouter(prefix="/v1", tags=["validate"])


@router.post("/validate", response_model=ValidateResponse)
def validate(
    req: ValidateRequest,
    validator: Any = Depends(get_validator),
    ignore_extras: bool = Query(False),
) -> object:
    """Validate input against the configured schema.

    Args:
        req (ValidateRequest): Request payload holding the spec to validate.
        validator (Any): Validator instance (duck-typed to our ``Validator`` API).
        ignore_extras (bool): If ``True``, drop unknown fields instead of reporting them.

    Returns:
        object: Mapping with ``ok``, a list of ``issues``, and ``normalized`` on success.
    """
    report = validator.validate(req.spec, raise_on_fail=False, ignore_extras=ignore_extras)

    issue_models = [
        IssueModel(
            code=i.code,
            path=list(i.path) if getattr(i, "path", None) else None,
            msg=i.msg,
            detail=getattr(i, "detail", None),
        )
        for i in getattr(report, "issues", [])
    ]

    return {
        "ok": bool(getattr(report, "ok", False)),
        "issues": issue_models,
        "normalized": getattr(report, "normalized", None) if getattr(report, "ok", False) else None,
    }
