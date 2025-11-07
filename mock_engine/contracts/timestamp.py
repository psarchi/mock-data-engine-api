from __future__ import annotations
from typing import ClassVar, Set, Optional
from datetime import datetime
from pydantic import ConfigDict
from mock_engine.contracts.base import ContractModel


class TimestampGeneratorSpec(ContractModel):
    """Timestamp generator (start/end datetimes)."""
    model_config = ConfigDict(extra="forbid")
    type_token: ClassVar[str] = "timestamp"
    type_aliases: ClassVar[Set[str]] = set()

    start: Optional[datetime] = None
    end: Optional[datetime] = None

    def to_spec(self, name: str, adapt):
        def enc(x):
            if x is None:
                return None
            if isinstance(x, (int, float, str)):
                return x
            if isinstance(x, datetime):
                return x.isoformat()
            return str(x)

        out: dict = {"type": "timestamp"}
        if self.start is not None:
            out["start"] = enc(self.start)
        if self.end is not None:
            out["end"] = enc(self.end)
        return out
