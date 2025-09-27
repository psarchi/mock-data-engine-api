from faker_engine.generators.gens.base import BaseGenerator
from faker_engine.generators.context import GenContext


class StringGenerator(BaseGenerator):
    __slots__ = ('string_type','min_length', 'max_length')
    __aliases__ = ('string', 'str')

    def __init__(self, string_type=None, min_length=None, max_length=None):
        self.min_length = min_length
        self.max_length = max_length
        self.string_type = string_type

    def _sanity_check(self, ctx):
        if self.min_length is not None and self.max_length is not None:
            if not isinstance(self.min_length, (int, float)):
                raise ValueError('min_value must be int or float')
            if not isinstance(self.max_length, (int, float)):
                raise ValueError('max_value must be int or float')
            if self.max_length < self.min_length:
                raise ValueError("max_value must be >= min_value")
        if not isinstance(ctx, GenContext):
            raise TypeError("ctx must be an instance of random.Random")

    def _resolve_faker_provider(self, string_type: str, ctx: GenContext):
        if not string_type:
            raise ValueError(
                "string_type must be provided for Faker-backed generation")

        provider_name = string_type.lower()
        fake = ctx.faker

        try:
            fn = getattr(fake, provider_name)
        except AttributeError:
            raise ValueError(f"Unknown Faker provider: '{string_type}'")

        if not callable(fn):
            raise TypeError(f"Faker attribute '{string_type}' is not callable")
        return fn

    def generate(self, ctx):
        self._sanity_check(ctx)
        if self.string_type:
            provider = self._resolve_faker_provider(self.string_type, ctx)
            output = provider()
            if not isinstance(output, str):
                raise TypeError(
                    f"Faker attribute '{self.string_type}' is not a string")
            return provider()
        else:
            from string import ascii_lowercase
            length = ctx.rng.randint(self.min_length if self.min_length is not None else 1,
                                     self.max_length if self.max_length is not None else 100)
            output = "".join(
                ctx.rng.choice(ascii_lowercase) for _ in range(length))
            return output
