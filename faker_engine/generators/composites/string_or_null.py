from faker_engine.errors import ContextError, MissingChildError, InvalidParameterError
from faker_engine.generators.base import BaseGenerator
from faker_engine.context import GenContext


class StringOrNullGenerator(BaseGenerator):
    __slots__ = ("child", "weights")
    __aliases__ = ("string_or_null",)

    def __init__(self, child=None, weights=None):
        # weights: [string_weight, null_weight]
        self.child = child
        self.weights = weights

    @classmethod
    def from_spec(cls, builder, spec):
        of_spec = spec.get("of")
        if of_spec is None:
            raise MissingChildError("string_or_null requires 'of' string spec")
        built = builder.build(of_spec)
        weights = spec.get("weights")  # optional two-item list
        return cls(child=built, weights=weights)

    def _sanity_check(self, ctx):
        if not isinstance(ctx, GenContext):
            raise ContextError("ctx must be an instance of GenContext")
        if self.child is None:
            raise MissingChildError("string_or_null requires a string child")
        if self.weights is None:
            return
        if not isinstance(self.weights, (list, tuple)) or len(self.weights) != 2:
            raise InvalidParameterError("weights must be a two-item list: [string, null]")
        try:
            total = float(self.weights[0]) + float(self.weights[1])
        except Exception:
            raise InvalidParameterError("weights must be numeric")
        if total <= 0:
            raise InvalidParameterError("sum(weights) must be > 0")

    def configure(self, child=None, weights=None, **kwargs):
        if child is not None:
            self.child = child
        if weights is not None:
            self.weights = weights
        return self

    def generate(self, ctx):
        self._sanity_check(ctx)
        if not self.weights:
            # default 50/50
            if ctx.rng.random() < 0.5:
                return None
            return self.child.generate(ctx)
        string_w, null_w = float(self.weights[0]), float(self.weights[1])
        total = string_w + null_w
        r = ctx.rng.random() * total
        if r < string_w:
            return self.child.generate(ctx)
        return None
