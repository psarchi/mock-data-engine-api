from mock_engine.generators.composites.one_of import OneOfGenerator
from mock_engine.context import GenContext


class A:
    def generate(self, ctx): return "A"


class B:
    def generate(self, ctx): return "B"


def test_one_of_uniform_pick():
    ctx = GenContext(seed=1)
    gen = OneOfGenerator(choices=[A(), B()])
    out = gen.generate(ctx)
    assert out in ("A", "B")


def test_one_of_weighted_pick_favors_b():
    ctx = GenContext(seed=1)
    gen = OneOfGenerator(choices=[A(), B()], weights=[1, 100])
    # With strong weight on B, the first pick should be B for this seed
    assert gen.generate(ctx) == "B"
