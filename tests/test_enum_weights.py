from faker_engine.generators.leafs.enum import EnumGenerator
from faker_engine.context import GenContext


def test_enum_weights_bias():
    ctx = GenContext(seed=3)
    gen = EnumGenerator(values=['x', 'y'], weights=[1, 100])
    assert gen.generate(ctx) == 'y'
