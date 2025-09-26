from faker_engine.generators.gens.base import BaseGenerator
from faker_engine.generators.context import GenContext


class BoolGenerator(BaseGenerator):
    __slots__: ()
    __aliases__ = ('bool',)

    def generate(self, ctx: GenContext):
        return ctx.rng.choice([True, False])
