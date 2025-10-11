from faker_engine.generators.composites.select import SelectGenerator
from faker_engine.context import GenContext

class DummyBuilder:
    def build(self, spec): return spec

class C:
    def __init__(self, v): self.v = v
    def generate(self, ctx): return self.v

def test_select_required_and_exact():
    ctx = GenContext(seed=9)
    options = {
        'req': {'of': C(1), 'required': True},
        'opt1': {'of': C(2)},
        'opt2': {'of': C(3)},
    }
    gen = SelectGenerator.from_spec(DummyBuilder(), {'options': options, 'pick': {'mode': 'exact', 'min': 1}})
    out = gen.generate(ctx)
    assert 'req' in out and len(out) == 2 and set(out.keys()).issubset({'req','opt1','opt2'})
