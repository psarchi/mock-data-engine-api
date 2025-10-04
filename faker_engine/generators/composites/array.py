# NOTE: ArrayGenerator not supported yet by legacy core
from faker_engine.generators.base import BaseGenerator
from faker_engine.context import GenContext


class ArrayGenerator(BaseGenerator):
    __slots__ = ("min_items", "max_items", "child")
    __aliases__ = ("array", "list")

    def __init__(self, min_items=None, max_items=None, child=None):
        self.min_items = min_items
        self.max_items = max_items
        self.child = child  # must be a generator instance

    @classmethod
    def from_spec(cls, builder, spec):
        child_spec = spec.get("child") or spec.get("of")
        if not child_spec:
            raise ValueError("Array spec requires 'child' or 'of'")
        child = builder.build(child_spec)
        return cls(
            min_items=spec.get("min_items"),
            max_items=spec.get("max_items"),
            child=child,
        )

    def _sanity_check(self, ctx):
        if not isinstance(ctx, GenContext):
            raise TypeError("ctx must be a GenContext")
        if self.min_items is not None and not isinstance(self.min_items, int):
            raise ValueError("min_items must be int")
        if self.max_items is not None and not isinstance(self.max_items, int):
            raise ValueError("max_items must be int")
        if self.min_items is not None and self.max_items is not None:
            if self.max_items < self.min_items:
                raise ValueError("max_items must be >= min_items")

    def configure(self, min_items=None, max_items=None, child=None, **kwargs):
        if min_items is not None:
            self.min_items = min_items
        if max_items is not None:
            self.max_items = max_items
        if child is not None:
            self.child = child
        return self

    def generate(self, ctx):
        if not isinstance(ctx, GenContext):
            raise TypeError("ctx must be a GenContext")
        self._sanity_check(ctx)
        minv = self.min_items or 0
        maxv = self.max_items or 0
        count = ctx.rng.randint(minv, maxv)
        return [self.child.generate(ctx) for _ in range(count)]
