from __future__ import annotations
from typing import ClassVar, Set, List, Any, Optional
from pydantic import ConfigDict
from mock_engine.contracts.base import ContractModel


class OneOfGeneratorSpec(ContractModel):
    """Union of structural variants; choices are full specs with optional weights."""
    model_config = ConfigDict(extra="forbid")
    type_token: ClassVar[str] = "one_of"
    type_aliases: ClassVar[Set[str]] = {"oneof"}

    choices: Optional[List[Any]] = None
    weights: Optional[List[float]] = None

    def to_spec(self, name: str, adapt):
        choices = [{"of": adapt(f"{name}|{i}", c)} for i, c in
                   enumerate(self.choices or [])]
        out = {"type": "one_of", "choices": choices}
        if self.weights:
            out["weights"] = list(self.weights)
        return out
