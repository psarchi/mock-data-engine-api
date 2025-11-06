import re
import random
from mock_engine.generators.composites.maybe import MaybeGenerator
from mock_engine.context import GenContext


class DummyChild:
    def generate(self, ctx):
        return "X"


def test_maybe_always_null():
    ctx = GenContext(seed=123)
    gen = MaybeGenerator(child=DummyChild(), p_null=1.0)
    assert gen.generate(ctx) is None


def test_maybe_never_null():
    ctx = GenContext(seed=123)
    gen = MaybeGenerator(child=DummyChild(), p_null=0.0)
    assert gen.generate(ctx) == "X"
