from __future__ import annotations
from typing import Optional

from faker_engine.errors import ContextError, InvalidParameterError
from faker_engine.generators.base import BaseGenerator
from faker_engine.context import GenContext


class IntGenerator(BaseGenerator):
    __slots__ = ("min", "max", "step")
    __aliases__ = ("int",)

    def __init__(self, min: Optional[int] = None, max: Optional[int] = None,
                 step: Optional[int] = None) -> None:
        self.min = 0 if min is None else int(min)
        self.max = 100 if max is None else int(max)
        self.step = 1 if step is None else int(step)

    @classmethod
    def from_spec(cls, builder: object,
                  spec: dict[str, object]) -> "IntGenerator":
        return cls(
            min=spec.get("min"),
            max=spec.get("max"),
            step=spec.get("step"),
        )

    def _sanity_check(self, ctx: GenContext) -> None:
        if not isinstance(ctx, GenContext):
            raise ContextError("ctx must be an instance of GenContext")
        if self.step <= 0:
            raise InvalidParameterError("step must be > 0")
        if self.min > self.max:
            raise InvalidParameterError("min must be <= max")
        span = self.max - self.min
        if span < 0:
            raise InvalidParameterError("invalid range")

    def configure(self, min: Optional[int] = None, max: Optional[int] = None,
                  step: Optional[int] = None,
                  **kwargs: object) -> "IntGenerator":
        if min is not None:
            self.min = int(min)
        if max is not None:
            self.max = int(max)
        if step is not None:
            self.step = int(step)
        return self

    def generate(self, ctx: GenContext) -> int:
        self._sanity_check(ctx)
        # map to discrete steps within [min, max]
        count = ((self.max - self.min) // self.step) + 1
        if count <= 0:
            raise InvalidParameterError("empty range for step")
        idx = ctx.rng.randint(0, count - 1)
        return self.min + idx * self.step
