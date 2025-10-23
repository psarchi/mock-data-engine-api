from __future__ import annotations
from typing import Any, Optional
from pydantic import BaseModel, Field


class ValidateRequest(BaseModel):
    spec: Any = Field(..., description="Generator spec to validate")


class Issue(BaseModel):
    code: str
    path: list[str | int] | None = None
    msg: str
    detail: dict[str, Any] | None = None


class ValidateResponse(BaseModel):
    ok: bool
    issues: list[Issue]
    normalized: dict[str, Any] | None = None


class GenerateRequest(BaseModel):
    spec: Any
    n: int = Field(1, ge=1, le=10000)
    seed: Optional[int] = None
    locale: str = "en_US"


class GenerateResponse(BaseModel):
    items: list[Any]
    count: int
