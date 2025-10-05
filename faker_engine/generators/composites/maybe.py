from faker_engine.errors import ContextError, MissingChildError, InvalidParameterError
from faker_engine.generators.base import BaseGenerator
from faker_engine.context import GenContext


class MaybeGenerator(BaseGenerator):
    __slots__ = ("child", "p_null")
    __aliases__ = ("maybe",)

    def __init__(self, child=None, p_null=None):
        self.child = child
        self.p_null = 0.1 if p_null is None else p_null

    @classmethod
    def from_spec(cls, builder, spec):
        of_spec = spec.get("of")
        if of_spec is None:
            raise MissingChildError("'of' is required for maybe generator")
        built = builder.build(of_spec)
        p = spec.get("p_null")
        return cls(child=built, p_null=p)

    def _sanity_check(self, ctx):
        if not isinstance(ctx, GenContext):
            raise ContextError("ctx must be an instance of GenContext")
        if self.child is None:
            raise MissingChildError("maybe requires a child generator")
        if self.p_null is None:
            self.p_null = 0.1
        if not (0.0 <= float(self.p_null) <= 1.0):
            raise InvalidParameterError("p_null must be between 0 and 1")

    def configure(self, child=None, p_null=None, **kwargs):
        if child is not None:
            self.child = child
        if p_null is not None:
            self.p_null = p_null
        return self

    def generate(self, ctx):
        self._sanity_check(ctx)
        if ctx.rng.random() < float(self.p_null):
            return None
        return self.child.generate(ctx)
