import re
from mock_engine.generators.leafs.string import StringGenerator
from mock_engine.context import GenContext

def test_string_template_upper_default():
    ctx = GenContext(seed=7)
    gen = StringGenerator(template='ISO-{nnn}')
    out = gen.generate(ctx)
    assert out.startswith('ISO-') and re.fullmatch(r'ISO-[A-Z]{3}', out)

def test_string_template_numeric():
    ctx = GenContext(seed=7)
    gen = StringGenerator(template='ID-{nn}', n_type='numeric')
    assert re.fullmatch(r'ID-[0-9]{2}', gen.generate(ctx))

def test_string_template_charset_override():
    ctx = GenContext(seed=7)
    gen = StringGenerator(template='PRD-{nnn}', n_charset='ABC')
    assert re.fullmatch(r'PRD-[ABC]{3}', gen.generate(ctx))

def test_string_regex_plain_only():
    ctx = GenContext(seed=11)
    gen = StringGenerator(regex=r'^[a-z0-9]{8}$', min_length=8, max_length=12, charset='abc0123456789')
    out = gen.generate(ctx)
    assert re.fullmatch(r'^[a-z0-9]{8}$', out)

def test_string_faker_provider_simple(monkeypatch):
    ctx = GenContext(seed=1)
    gen = StringGenerator(string_type='first_name')
    # Monkeypatch provider resolver to return a stub function
    monkeypatch.setattr(StringGenerator, '_resolve_faker_provider', lambda self, st, c: (lambda: 'Alice'))
    assert gen.generate(ctx) == 'Alice'
