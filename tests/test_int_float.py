from mock_engine.generators.leafs.int import IntGenerator
from mock_engine.generators.leafs.float import FloatGenerator
from mock_engine.context import GenContext


def test_int_step_progression():
    ctx = GenContext(seed=5)
    gen = IntGenerator(min=0, max=10, step=5)
    val = gen.generate(ctx)
    assert val in {0, 5, 10}


def test_float_precision():
    ctx = GenContext(seed=1)
    gen = FloatGenerator(min=0.0, max=1.0, precision=3)
    val = gen.generate(ctx)
    assert isinstance(val, float)
    # exactly 3 decimal places when stringified in simple cases
    s = f"{val:.3f}"
    assert len(s.split('.')[1]) == 3
