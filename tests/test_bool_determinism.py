
from faker_engine.generators.leaf.leaf_logical import BoolGenerator
from faker_engine.context import GenContext

def test_bool_deterministic_sequence():
    gen = BoolGenerator()
    ctx1 = GenContext(seed=123)
    ctx2 = GenContext(seed=123)
    seq1 = [gen.generate(ctx1) for _ in range(20)]
    seq2 = [gen.generate(ctx2) for _ in range(20)]
    assert seq1 == seq2
    assert all(isinstance(x, bool) for x in seq1)
