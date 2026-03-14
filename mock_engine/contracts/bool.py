from __future__ import annotations
from typing import ClassVar, Optional, Set
from pydantic import ConfigDict
from mock_engine.contracts.base import ContractModel


class BoolGeneratorSpec(ContractModel):
    """Boolean generator."""

    model_config = ConfigDict(extra="forbid")
    type_token: ClassVar[str] = "bool"
    type_aliases: ClassVar[Set[str]] = {"boolean"}
    bound_to: Optional[str] = None
    linked_to: Optional[str] = None
    bound_to_schema: Optional[str] = None
    bound_to_revision: Optional[int] = None
