from faker_engine.errors import ContextError, MissingChildError, InvalidParameterError
from faker_engine.generators.base import BaseGenerator
from faker_engine.context import GenContext


class ObjectGenerator(BaseGenerator):
    __slots__ = ("_built", "_meta")
    __aliases__ = ("object",)

    def __init__(self, fields=None):
        # fields stored as: built[name] -> child generator; meta[name] -> {required, default}
        self._built = fields or {}
        self._meta = {}

    @classmethod
    def from_spec(cls, builder, spec):
        fields = spec.get("fields")
        if not fields or not isinstance(fields, dict):
            raise MissingChildError("object requires 'fields' dict")
        built = {}
        meta = {}
        # preserve insertion order by iterating given dict
        for name, conf in fields.items():
            if isinstance(conf, dict) and "of" in conf:
                built[name] = builder.build(conf.get("of"))
                meta[name] = {
                    "required": bool(conf.get("required")),
                    "default": conf.get("default", None),
                }
            else:
                # shorthand: conf itself is a spec
                built[name] = builder.build(conf)
                meta[name] = {"required": False, "default": None}
        obj = cls(fields=built)
        obj._meta = meta
        return obj

    def _sanity_check(self, ctx):
        if not isinstance(ctx, GenContext):
            raise ContextError("ctx must be an instance of GenContext")
        if not self._built:
            raise MissingChildError("object has no fields")

    def configure(self, fields=None, **kwargs):
        if fields is not None:
            # expect same {name: generator} shape; caller responsible
            self._built = fields
        return self

    def generate(self, ctx):
        self._sanity_check(ctx)
        out = {}
        # stable order: iterate in insertion order of self._built
        for name, gen in self._built.items():
            m = self._meta.get(name, {})
            required = bool(m.get("required"))
            default = m.get("default", None)
            value = gen.generate(ctx)
            if value is None:
                if default is not None:
                    value = default
                elif required:
                    raise InvalidParameterError("required field '%s' generated None" % name)
            out[name] = value
        return out

