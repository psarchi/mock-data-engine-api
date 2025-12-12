from __future__ import annotations
from typing import ClassVar, Set, Any, Optional, List
from pydantic import ConfigDict
from mock_engine.contracts.base import ContractModel


class ObjectOrNullGeneratorSpec(ContractModel):
    """Typed nullable shortcut for object."""

    model_config = ConfigDict(extra="forbid")
    type_token: ClassVar[str] = "object_or_null"
    type_aliases: ClassVar[Set[str]] = set()

    child: Optional[Any] = None
    weights: Optional[List[float]] = None

    def to_spec(self, name: str, adapt):
        out = {"type": "object_or_null"}
        if self.child is not None:
            out["child"] = adapt(f"{name}.?", self.child)
        if self.weights is not None:
            out["weights"] = self.weights
        return out
