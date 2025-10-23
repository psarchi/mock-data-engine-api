from __future__ import annotations
from fastapi import APIRouter, Depends
from server.models import ValidateRequest, ValidateResponse, \
    Issue as IssueModel
from server.deps import get_validator

router = APIRouter(prefix="/v1", tags=["validate"])


@router.post("/validate", response_model=ValidateResponse)
def validate(req: ValidateRequest, validator=Depends(get_validator)):
    report = validator.validate(req.spec, raise_on_fail=False)
    issues = [
        IssueModel(code=i.code,
                   path=list(i.path) if getattr(i, "path", None) else None,
                   msg=i.msg, detail=getattr(i, "detail", None))
        for i in report.issues
    ]
    return {"ok": report.ok, "issues": issues,
            "normalized": report.normalized if report.ok else None}
