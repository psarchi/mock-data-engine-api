from faker_engine.errors import OutOfBoundsError, ContextError, InvalidParameterError
from faker_engine.generators.base import BaseGenerator
from faker_engine.context import GenContext

class FloatGenerator(BaseGenerator):
    __slots__ = ('min_value', 'max_value', 'decimal_places')
    __aliases__ = ('float', 'double')

    def __init__(self, min_value=None, max_value=None, decimal_places=2):
        self.min_value = min_value
        self.max_value = max_value
        self.decimal_places = decimal_places

    def _sanity_check(self, ctx):
        if self.min_value is not None and self.max_value is not None:
            if not isinstance(self.min_value, (int, float)):
                raise InvalidParameterError('min_value must be int or float')
            if not isinstance(self.max_value, (int, float)):
                raise InvalidParameterError('max_value must be int or float')
            if self.max_value < self.min_value:
                raise OutOfBoundsError("max_value must be >= min_value")
        if self.decimal_places is not None and not isinstance(self.decimal_places, int):
            raise InvalidParameterError('decimal_places must be int')
        if not isinstance(ctx, GenContext):
            raise ContextError("ctx must be an instance of GenContext")

    def generate(self, ctx):
        self._sanity_check(ctx)
        if self.min_value is not None and self.max_value is not None:
            output = round(ctx.rng.uniform(float(self.min_value), float(self.max_value)), self.decimal_places or 0)
        else:
            lo = float(self.min_value) if self.min_value is not None else 1.0
            hi = float(self.max_value) if self.max_value is not None else 100.0
            output = round(ctx.rng.uniform(lo, hi), self.decimal_places or 0)
        self.reset()
        return output