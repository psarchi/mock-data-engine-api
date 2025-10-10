from faker_engine.errors import ContextError, InvalidParameterError
from faker_engine.generators.base import BaseGenerator
from faker_engine.context import GenContext


class FloatGenerator(BaseGenerator):
    __slots__ = ("min", "max", "precision")
    __aliases__ = ("float",)

    def __init__(self, min=None, max=None, precision=None):
        self.min = 0.0 if min is None else float(min)
        self.max = 1.0 if max is None else float(max)
        self.precision = None if precision is None else int(precision)

    @classmethod
    def from_spec(cls, builder, spec):
        return cls(
            min=spec.get("min"),
            max=spec.get("max"),
            precision=spec.get("precision"),
        )

    def _sanity_check(self, ctx):
        if not isinstance(ctx, GenContext):
            raise ContextError("ctx must be an instance of GenContext")
        if self.min > self.max:
            raise InvalidParameterError("min must be <= max")
        if self.precision is not None and self.precision < 0:
            raise InvalidParameterError("precision must be >= 0")

    def configure(self, min=None, max=None, precision=None, **kwargs):
        if min is not None:
            self.min = float(min)
        if max is not None:
            self.max = float(max)
        if precision is not None:
            self.precision = int(precision)
        return self

    def generate(self, ctx):
        self._sanity_check(ctx)
        value = ctx.rng.random() * (self.max - self.min) + self.min
        if self.precision is not None:
            return round(value, self.precision)
        return value