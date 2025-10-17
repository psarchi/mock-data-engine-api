from faker_engine.errors import ContextError, InvalidParameterError
from faker_engine.generators.base import BaseGenerator
from faker_engine.context import GenContext


class IntGenerator(BaseGenerator):
    
    __meta__ = {
        'aliases': {
        'max': 'max',
        'min': 'min',
        'step': 'step',
        },
        'deprecations': [],
        'rules': [],
        # TODO: introduce per-generator versioning (SemVer) once contracts stabilize.
    }
    __slots__ = ("min", "max", "step")
    __aliases__ = ("int",)

    def __init__(self, min=None, max=None, step=None):
        self.min = 0 if min is None else int(min)
        self.max = 100 if max is None else int(max)
        self.step = 1 if step is None else int(step)

    @classmethod
    def from_spec(cls, builder, spec):
        return cls(
            min=spec.get("min"),
            max=spec.get("max"),
            step=spec.get("step"),
        )

    def _sanity_check(self, ctx):
        if not isinstance(ctx, GenContext):
            raise ContextError("ctx must be an instance of GenContext")
        if self.step <= 0:
            raise InvalidParameterError("step must be > 0")
        if self.min > self.max:
            raise InvalidParameterError("min must be <= max")
        span = self.max - self.min
        if span < 0:
            raise InvalidParameterError("invalid range")

    def configure(self, min=None, max=None, step=None, **kwargs):
        if min is not None:
            self.min = int(min)
        if max is not None:
            self.max = int(max)
        if step is not None:
            self.step = int(step)
        return self

    def generate(self, ctx):
        self._sanity_check(ctx)
        # map to discrete steps within [min, max]
        count = ((self.max - self.min) // self.step) + 1
        if count <= 0:
            raise InvalidParameterError("empty range for step")
        idx = ctx.rng.randint(0, count - 1)
        return self.min + idx * self.step