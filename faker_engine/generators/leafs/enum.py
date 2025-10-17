from faker_engine.errors import ContextError, MissingChildError, InvalidParameterError
from faker_engine.generators.base import BaseGenerator
from faker_engine.context import GenContext


class EnumGenerator(BaseGenerator):
    
    __meta__ = {
        'aliases': {
        'values': 'values',
        'weights': 'weights',
        },
        'deprecations': [],
        'rules': [],
        # TODO: introduce per-generator versioning (SemVer) once contracts stabilize.
    }
    __slots__ = ("values", "weights")
    __aliases__ = ("enum",)

    def __init__(self, values=None, weights=None):
        self.values = list(values) if values else []
        self.weights = list(weights) if weights else None

    @classmethod
    def from_spec(cls, builder, spec):
        vals = spec.get("values")
        if not vals or not isinstance(vals, list):
            raise MissingChildError("enum requires 'values' list")
        return cls(values=vals, weights=spec.get("weights"))

    def _sanity_check(self, ctx):
        if not isinstance(ctx, GenContext):
            raise ContextError("ctx must be an instance of GenContext")
        if not self.values:
            raise MissingChildError("enum has no values")
        if self.weights is None:
            return
        if not isinstance(self.weights, (list, tuple)):
            raise InvalidParameterError("weights must be a list")
        if len(self.weights) != len(self.values):
            raise InvalidParameterError("weights length must match values")
        try:
            total = float(sum(self.weights))
        except Exception:
            raise InvalidParameterError("weights must be numeric")
        if total <= 0:
            raise InvalidParameterError("sum(weights) must be > 0")

    def configure(self, values=None, weights=None, **kwargs):
        if values is not None:
            self.values = list(values)
        if weights is not None:
            self.weights = list(weights)
        return self

    def _pick_index(self, rng):
        if not self.weights:
            return rng.randint(0, len(self.values) - 1)
        total = float(sum(self.weights))
        r = rng.random() * total
        acc = 0.0
        for idx, w in enumerate(self.weights):
            acc += float(w)
            if r <= acc:
                return idx
        return len(self.values) - 1

    def generate(self, ctx):
        self._sanity_check(ctx)
        idx = self._pick_index(ctx.rng)
        return self.values[idx]
