from __future__ import annotations
from typing import ClassVar, Set, List, Any, Optional
from pydantic import ConfigDict
from mock_engine.contracts.base import ContractModel


class EnumGeneratorSpec(ContractModel):
    """Literal set (values)."""
    model_config = ConfigDict(extra="forbid")
    type_token: ClassVar[str] = "enum"
    type_aliases: ClassVar[Set[str]] = set()

    values: Optional[List[Any]] = None

    def to_spec(self, name: str, adapt):
        return {"type": "enum", "choices": list(self.values or [])}
