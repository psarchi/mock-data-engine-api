from faker_engine.errors import ContextError, MissingChildError, InvalidParameterError
from faker_engine.generators.base import BaseGenerator
from faker_engine.context import GenContext


class OneOfGenerator(BaseGenerator):
    
    __meta__ = {
        'aliases': {
        'choices': 'choices',
        'of': 'choices',
        },
        'deprecations': [],
        'rules': [],
        # TODO: introduce per-generator versioning (SemVer) once contracts stabilize.
    }
    __slots__ = ("choices", "weights")
    __aliases__ = ("one_of",)

    def __init__(self, choices=None, weights=None):
        self.choices = choices or []
        self.weights = weights

    @classmethod
    def from_spec(cls, builder, spec):
        raw = spec.get("choices")
        if not raw or not isinstance(raw, list):
            raise MissingChildError("'choices' (list) is required for one_of")
        built = []
        for item in raw:
            child_spec = item.get("of") if isinstance(item, dict) else None
            if child_spec is None:
                raise MissingChildError("each choice must provide 'of'")
            built.append(builder.build(child_spec))
        weights = spec.get("weights")
        return cls(choices=built, weights=weights)

    def _sanity_check(self, ctx):
        if not isinstance(ctx, GenContext):
            raise ContextError("ctx must be an instance of GenContext")
        if not self.choices:
            raise MissingChildError("one_of requires at least one child")
        if self.weights is None:
            return
        if not isinstance(self.weights, (list, tuple)):
            raise InvalidParameterError("weights must be a list")
        if len(self.weights) != len(self.choices):
            raise InvalidParameterError("weights length must match choices")
        try:
            total = float(sum(self.weights))
        except Exception:
            raise InvalidParameterError("weights must be numeric")
        if total <= 0:
            raise InvalidParameterError("sum(weights) must be > 0")

    def configure(self, choices=None, weights=None, **kwargs):
        if choices is not None:
            self.choices = choices
        if weights is not None:
            self.weights = weights
        return self

    def _pick_index(self, rng):
        if not self.weights:
            return rng.randint(0, len(self.choices) - 1)
        # weighted pick without external deps
        total = float(sum(self.weights))
        r = rng.random() * total
        acc = 0.0
        for idx, w in enumerate(self.weights):
            acc += float(w)
            if r <= acc:
                return idx
        return len(self.choices) - 1

    def generate(self, ctx):
        self._sanity_check(ctx)
        idx = self._pick_index(ctx.rng)
        return self.choices[idx].generate(ctx)