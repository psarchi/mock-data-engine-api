from faker_engine.generators.base import BaseGenerator
from faker_engine.generators.context import GenContext


class EnumGenerator(BaseGenerator):
    __slots__ = 'list_of_items'
    __aliases__ = ('enum',)

    def __init__(self, list_of_items=None):
        self.list_of_items = list_of_items

    def _sanity_check(self, ctx):
        if not self.list_of_items:
            raise ValueError(f"No items given for for enum Generator")
        if not isinstance(self.list_of_items, list):
            raise ValueError(f"List given for enum Generator")
        if not isinstance(ctx, GenContext):
            raise TypeError("ctx must be an instance of random.Random")

    def generate(self, ctx: GenContext):
        self._sanity_check(ctx)
        return ctx.rng.choice(self.list_of_items)
