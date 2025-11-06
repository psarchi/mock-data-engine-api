from mock_engine.generators.leafs.int import IntGenerator
from mock_engine.context import GenContext


def test_int_within_bounds():
    ctx = GenContext(seed=123)
    gen = IntGenerator(min=1, max=5)
    for _ in range(100):
        v = gen.generate(ctx)
        assert 1 <= v <= 5
