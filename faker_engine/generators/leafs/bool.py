from faker_engine.errors import ContextError, InvalidParameterError
from faker_engine.generators.base import BaseGenerator
from faker_engine.context import GenContext


class BoolGenerator(BaseGenerator):
    
    __meta__ = {
        'aliases': {
        'p_true': 'p_true',
        },
        'deprecations': [],
        'rules': [],
        # TODO: introduce per-generator versioning (SemVer) once contracts stabilize.
    }
    __slots__ = ("p_true",)
    __aliases__ = ("bool",)

    def __init__(self, p_true=None):
        self.p_true = 0.5 if p_true is None else p_true

    @classmethod
    def from_spec(cls, builder, spec):
        return cls(p_true=spec.get("p_true"))

    def _sanity_check(self, ctx):
        if not isinstance(ctx, GenContext):
            raise ContextError("ctx must be an instance of GenContext")
        if not (0.0 <= float(self.p_true) <= 1.0):
            raise InvalidParameterError("p_true must be between 0 and 1")

    def configure(self, p_true=None, **kwargs):
        if p_true is not None:
            self.p_true = p_true
        return self

    def generate(self, ctx):
        self._sanity_check(ctx)
        return ctx.rng.random() < float(self.p_true)
