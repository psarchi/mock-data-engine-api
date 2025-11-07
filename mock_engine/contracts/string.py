from __future__ import annotations
from typing import ClassVar, Set, Optional
from pydantic import ConfigDict
from mock_engine.contracts.base import ContractModel


class StringGeneratorSpec(ContractModel):
    """String generator.
    Supports templates, regex, length bounds, and provider shortcuts via string_type/n_type.
    """
    model_config = ConfigDict(extra="forbid")
    type_token: ClassVar[str] = "string"
    type_aliases: ClassVar[Set[str]] = {"str", "text"}

    template: Optional[str] = None
    regex: Optional[str] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    string_type: Optional[str] = None  # e.g., city, state, url, uuid4, word
    n_type: Optional[str] = None  # e.g., numeric templating helper
