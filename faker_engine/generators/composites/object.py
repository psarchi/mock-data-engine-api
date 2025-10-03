# NOTE: ObjectGenerator not supported yet by legacy core
from faker_engine.generators.base import BaseGenerator
from faker_engine.context import GenContext

class ObjectGenerator(BaseGenerator):
    __slots__ = ("fields",)
    __aliases__ = ("object", "dict")

    def __init__(self, fields=None):
        self.fields = fields or {}

    @classmethod
    def from_spec(cls, builder, spec):
        raw = spec.get("fields", {})
        built = {}
        for name, child_spec in raw.items():
            built[name] = builder.build(child_spec)
        return cls(fields=built)

    def configure(self, fields=None, **kwargs):
        if fields is not None:
            self.fields = fields
        return self

    def generate(self, ctx):
        if not isinstance(ctx, GenContext):
            raise TypeError("ctx must be an instance of GenContext")
        return {name: gen.generate(ctx) for name, gen in self.fields.items()}
