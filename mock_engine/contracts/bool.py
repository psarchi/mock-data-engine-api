from __future__ import annotations
from typing import ClassVar, Set
from pydantic import ConfigDict
from mock_engine.contracts.base import ContractModel


class BoolGeneratorSpec(ContractModel):
    """Boolean generator."""
    model_config = ConfigDict(extra="forbid")
    type_token: ClassVar[str] = "bool"
    type_aliases: ClassVar[Set[str]] = {"boolean"}
