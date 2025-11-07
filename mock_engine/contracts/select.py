from __future__ import annotations
from typing import ClassVar, Set, Dict, Any, Optional
from pydantic import ConfigDict
from mock_engine.contracts.base import ContractModel


class SelectGeneratorSpec(ContractModel):
    """Pick-k-of-N named branches."""
    model_config = ConfigDict(extra="forbid")
    type_token: ClassVar[str] = "select"
    type_aliases: ClassVar[Set[str]] = set()

    options: Optional[Dict[str, Any]] = None
    pick: Optional[int] = None

    def to_spec(self, name: str, adapt):
        options = {}
        for k, v in (self.options or {}).items():
            options[k] = adapt(f"{name}.{k}", v)
        out = {"type": "select", "options": options}
        if self.pick is not None:
            out["pick"] = self.pick
        return out
