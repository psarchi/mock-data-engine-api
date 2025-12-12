from __future__ import annotations
from typing import ClassVar, Set, Optional
from pydantic import ConfigDict
from mock_engine.contracts.base import ContractModel


class DateTimeGeneratorSpec(ContractModel):
    """Date/time generator (format optional)."""

    model_config = ConfigDict(extra="forbid")
    type_token: ClassVar[str] = "datetime"
    type_aliases: ClassVar[Set[str]] = set()

    format: Optional[str] = None
    depends_on: Optional[str] = None
