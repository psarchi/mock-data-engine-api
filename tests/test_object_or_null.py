from faker_engine.generators.composites.object_or_null import \
    ObjectOrNullGenerator
from faker_engine.generators.composites.object import ObjectGenerator
from faker_engine.context import GenContext


class FixedField:
    def __init__(self, value): self.value = value

    def generate(self, ctx): return self.value


def test_object_or_null_all_null():
    ctx = GenContext(seed=42)
    child = ObjectGenerator(fields={'id': FixedField(1)})
    gen = ObjectOrNullGenerator(child=child, p_null=1.0)
    assert gen.generate(ctx) is None


def test_object_or_null_object_generated():
    ctx = GenContext(seed=42)
    child = ObjectGenerator(fields={'id': FixedField(1)})
    gen = ObjectOrNullGenerator(child=child, p_null=0.0)
    assert gen.generate(ctx) == {'id': 1}
