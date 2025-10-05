from faker_engine.errors import ContextError, MissingChildError, InvalidParameterError
from faker_engine.generators.base import BaseGenerator
from faker_engine.context import GenContext


class ObjectOrNullGenerator(BaseGenerator):
    __slots__ = ("child", "p_null")
    __aliases__ = ("object_or_null",)

    def __init__(self, child=None, p_null=None):
        self.child = child
        self.p_null = 0.1 if p_null is None else p_null

    @classmethod
    def from_spec(cls, builder, spec):
        # Accept either direct object spec via 'of' or sugar via 'fields'
        of_spec = spec.get("of")
        fields = spec.get("fields")
        if of_spec is None and fields is None:
            raise MissingChildError("object_or_null requires 'fields' or 'of'")
        if of_spec is None:
            of_spec = {"kind": "object", "fields": fields}
        built = builder.build(of_spec)
        p = spec.get("p_null")
        return cls(child=built, p_null=p)

    def _sanity_check(self, ctx):
        if not isinstance(ctx, GenContext):
            raise ContextError("ctx must be an instance of GenContext")
        if self.child is None:
            raise MissingChildError("object_or_null requires an object child")
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


