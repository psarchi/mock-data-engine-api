from faker_engine.errors import EmptyEnumError, ContextError, \
    InvalidParameterError
from faker_engine.generators.base import BaseGenerator
from faker_engine.context import GenContext


class EnumGenerator(BaseGenerator):
    __slots__ = 'list_of_items'
    __aliases__ = ('enum',)

    def __init__(self, list_of_items=None):
        self.list_of_items = list_of_items

    def _sanity_check(self, ctx):
        if not self.list_of_items:
            raise EmptyEnumError("No items given for enum generator")
        if not isinstance(self.list_of_items, list):
            raise InvalidParameterError("list_of_items must be a list")
        if not isinstance(ctx, GenContext):
            raise ContextError("ctx must be an instance of GenContext")

    def generate(self, ctx):
        self._sanity_check(ctx)
        return ctx.rng.choice(self.list_of_items)
