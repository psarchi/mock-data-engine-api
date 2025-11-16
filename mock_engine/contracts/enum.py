from __future__ import annotations
from typing import ClassVar, Set, List, Any, Optional
from pydantic import ConfigDict
from mock_engine.contracts.base import ContractModel


class EnumGeneratorSpec(ContractModel):
    """Literal set (values) with optional weights."""
    model_config = ConfigDict(extra="forbid")
    type_token: ClassVar[str] = "enum"
    type_aliases: ClassVar[Set[str]] = set()

    values: Optional[List[Any]] = None
    weights: Optional[List[float]] = None

    def to_spec(self, name: str, adapt):
        payload = {"type": "enum", "choices": list(self.values or [])}
        if self.weights is not None:
            payload["weights"] = list(self.weights)
        return payload
