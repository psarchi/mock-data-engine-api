from faker_engine.errors import OutOfBoundsError, ContextError, \
    InvalidParameterError
from faker_engine.generators.base import BaseGenerator
from faker_engine.context import GenContext


class IntGenerator(BaseGenerator):
    __slots__ = ('min_value', 'max_value')
    __aliases__ = ('int', 'integer')

    def __init__(self, min_value=None, max_value=None):
        self.min_value = min_value
        self.max_value = max_value

    def _sanity_check(self, ctx):
        if self.min_value is not None and self.max_value is not None:
            if not isinstance(self.min_value, (int, float)):
                raise InvalidParameterError('min_value must be int or float')
            if not isinstance(self.max_value, (int, float)):
                raise InvalidParameterError('max_value must be int or float')
            if self.max_value < self.min_value:
                raise OutOfBoundsError("max_value must be >= min_value")
        if not isinstance(ctx, GenContext):
            raise ContextError("ctx must be an instance of GenContext")

    def generate(self, ctx):
        self._sanity_check(ctx)
        if self.min_value is not None and self.max_value is not None:
            output = ctx.rng.randint(int(self.min_value), int(self.max_value))
        else:
            lo = int(self.min_value) if self.min_value is not None else 1
            hi = int(self.max_value) if self.max_value is not None else 100
            output = ctx.rng.randint(lo, hi)
        self.reset()
        return output
