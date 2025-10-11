import pytest
from faker_engine.generators.composites.object import ObjectGenerator
from faker_engine.errors import InvalidParameterError
from faker_engine.context import GenContext

class DummyBuilder:
    def build(self, spec): return spec

class NullChild:
    def generate(self, ctx): return None
class Fixed:
    def __init__(self, v): self.v = v
    def generate(self, ctx): return self.v

def test_object_required_raises_on_none():
    ctx = GenContext(seed=1)
    spec = {'fields': {'a': {'of': NullChild(), 'required': True}}}
    gen = ObjectGenerator.from_spec(DummyBuilder(), spec)
    with pytest.raises(InvalidParameterError):
        gen.generate(ctx)

def test_object_default_applied():
    ctx = GenContext(seed=1)
    spec = {'fields': {'a': {'of': NullChild(), 'default': 7},
                       'b': {'of': Fixed(2), 'required': True}}}
    gen = ObjectGenerator.from_spec(DummyBuilder(), spec)
    assert gen.generate(ctx) == {'a': 7, 'b': 2}
