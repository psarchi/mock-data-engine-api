
from faker_engine.generators.leaf.leaf_numeric import IntGenerator
from faker_engine.context import GenContext

def test_int_within_bounds():
    gen = IntGenerator(min_value=1, max_value=5)
    ctx = GenContext(seed=999)
    vals = [gen.generate(ctx) for _ in range(10)]
    for v in vals:
        assert v >= 1 and v <= 5
