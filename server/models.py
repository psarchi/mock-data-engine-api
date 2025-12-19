"""Pydantic models for request/response payloads.

Defines input and output schemas used by the public API routes.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

__all__ = [
    "ValidateRequest",
    "Issue",
    "ValidateResponse",
    "GenerateRequest",
    "GenerateResponse",
]


class ValidateRequest(BaseModel):
    """Validation request payload.

    Attributes:
        spec (Any): Generator spec to validate.
    """

    spec: Any = Field(..., description="Generator spec to validate")


class Issue(BaseModel):
    """Validation issue item.

    Attributes:
        code (str): Machine-readable issue code.
        path (list[str | int] | None): Location of the issue inside the spec (tuple-like path).
        msg (str): Human-readable message.
        detail (dict[str, Any] | None): Optional extra details for the issue code.
    """

    code: str
    path: list[str | int] | None = None
    msg: str
    detail: dict[str, Any] | None = None


class ValidateResponse(BaseModel):
    """Validation response payload.

    Attributes:
        ok (bool): Overall validation status.
        issues (list[Issue]): List of issues (empty when ``ok`` is ``True``).
        normalized (dict[str, Any] | None): Normalized spec (present when ``ok`` is ``True``).
    """

    ok: bool
    issues: list[Issue]
    normalized: dict[str, Any] | None = None


class GenerateRequest(BaseModel):
    """Generation request payload.

    Attributes:
        spec (Any): Generator spec to build and run.
        n (int): Number of items to generate (``1..10000``).
        seed (int | None): Optional RNG seed for determinism.
        locale (str): Faker locale (e.g., ``"en_US"``).
    """

    spec: Any
    n: int = Field(1, ge=1, le=10000, description="Number of items to generate")
    seed: int | None = Field(None, description="Optional RNG seed for determinism")
    locale: str = Field("en_US", description="Faker locale identifier")


class GenerateResponse(BaseModel):
    """Generation response payload.

    Attributes:
        items (list[Any]): Generated items.
        count (int): Count of items returned.
    """

    items: list[Any]
    count: int
