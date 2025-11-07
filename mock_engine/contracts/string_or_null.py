from __future__ import annotations
from typing import ClassVar, Set, Any, Optional, List
from pydantic import ConfigDict
from mock_engine.contracts.base import ContractModel


class StringOrNullGeneratorSpec(ContractModel):
    """Typed nullable shortcut for string."""
    model_config = ConfigDict(extra="forbid")
    type_token: ClassVar[str] = "string_or_null"
    type_aliases: ClassVar[Set[str]] = set()

    child: Optional[Any] = None
    weights: Optional[List[float]] = None

    def to_spec(self, name: str, adapt):
        out = {"type": "string_or_null"}
        if self.child is not None:
            out["child"] = adapt(f"{name}.?", self.child)
        if self.weights is not None:
            out["weights"] = self.weights
        return out
