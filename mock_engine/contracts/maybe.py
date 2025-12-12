from __future__ import annotations
from typing import ClassVar, Set, Any, Optional
from pydantic import ConfigDict
from mock_engine.contracts.base import ContractModel


class MaybeGeneratorSpec(ContractModel):
    """Optional wrapper with probability of null (p_null)."""

    model_config = ConfigDict(extra="forbid")
    type_token: ClassVar[str] = "maybe"
    type_aliases: ClassVar[Set[str]] = set()

    child: Optional[Any] = None
    p_null: Optional[float] = None

    def to_spec(self, name: str, adapt):  # <- REQUIRED
        out = {"type": "maybe"}
        if self.child is not None:
            out["child"] = adapt(f"{name}.?", self.child)  # (or "of" if you prefer)
        if self.p_null is not None:
            out["p_null"] = self.p_null
        return out
