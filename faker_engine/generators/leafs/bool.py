from __future__ import annotations
from typing import Optional

from faker_engine.errors import ContextError, InvalidParameterError
from faker_engine.generators.base import BaseGenerator
from faker_engine.context import GenContext


class BoolGenerator(BaseGenerator):
    __slots__ = ("p_true",)
    __aliases__ = ("bool",)

    def __init__(self, p_true: Optional[float | int] = None) -> None:
        self.p_true = 0.5 if p_true is None else p_true

    @classmethod
    def from_spec(cls, builder: object,
                  spec: dict[str, object]) -> "BoolGenerator":
        return cls(p_true=spec.get("p_true"))

    def _sanity_check(self, ctx: GenContext) -> None:
        if not isinstance(ctx, GenContext):
            raise ContextError("ctx must be an instance of GenContext")
        if not (0.0 <= float(self.p_true) <= 1.0):
            raise InvalidParameterError("p_true must be between 0 and 1")

    def configure(self, p_true: Optional[float | int] = None,
                  **kwargs: object) -> "BoolGenerator":
        if p_true is not None:
            self.p_true = p_true
        return self

    def generate(self, ctx: GenContext) -> bool:
        self._sanity_check(ctx)
        return ctx.rng.random() < float(self.p_true)
