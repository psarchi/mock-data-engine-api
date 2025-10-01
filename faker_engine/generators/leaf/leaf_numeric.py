from faker_engine.generators.base import BaseGenerator
from faker_engine.generators.context import GenContext

class IntGenerator(BaseGenerator):
    __slots__ = ('min_value', 'max_value', 'decimal_places')
    __aliases__ = ('int', 'integer')

    def __init__(self, min_value=None, max_value=None):
        self.min_value = min_value
        self.max_value = max_value

    def _sanity_check(self, ctx):
        if self.min_value is not None and self.max_value is not None:
            if not isinstance(self.min_value,  (int, float)):
                raise ValueError('min_value must be int or float')
            if not isinstance(self.max_value,  (int, float)):
                raise ValueError('max_value must be int or float')
            if self.max_value < self.min_value:
                raise ValueError("max_value must be >= min_value")
        if not isinstance(ctx, GenContext):
            raise TypeError("ctx must be an instance of random.Random")

    def generate(self, ctx):
        self._sanity_check(ctx)
        if self.min_value is not None and self.max_value is not None:
            output = ctx.rng.randint(self.min_value, self.max_value)
        else:
            min = self.min_value if self.min_value is not None else 1
            max = self.max_value if self.max_value is not None else 100
            output = ctx.rng.randint(min, max)

        self.reset()
        return output


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
                raise ValueError('min_value must be int or float')
            if not isinstance(self.max_value,  (int, float)):
                raise ValueError('max_value must be int or float')
            if self.max_value < self.min_value:
                raise ValueError("max_value must be >= min_value")
        if not isinstance(ctx,GenContext):
            raise TypeError("ctx must be an instance of random.Random")

    def generate(self, ctx):
        self._sanity_check(ctx)
        if self.min_value is not None and self.max_value is not None:
            output = round(ctx.rng.uniform(self.min_value, self.max_value),
                           self.decimal_places)
            return output
        else:
            min = self.min_value if self.min_value is not None else 1.0
            max = self.max_value if self.max_value is not None else 100.0
            output = round(ctx.rng.uniform(min, max), self.decimal_places)
        self.reset()
        return output
