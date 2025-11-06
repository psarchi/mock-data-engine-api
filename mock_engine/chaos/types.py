from __future__ import annotations
from typing import Literal

ChaosScope = Literal['generate', 'validate', 'schema', 'admin']


class ChaosOpPhase:
    """Chaos Op Phase."""
    REQUEST = 'request'
    RESPONSE = 'response'
