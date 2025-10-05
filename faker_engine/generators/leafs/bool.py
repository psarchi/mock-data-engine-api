from faker_engine.errors import ContextError
from faker_engine.generators.base import BaseGenerator
from faker_engine.context import GenContext


class BoolGenerator(BaseGenerator):
    __slots__ = ()
    __aliases__ = ('bool',)

    def generate(self, ctx: GenContext):
        return ctx.rng.choice([True, False])
