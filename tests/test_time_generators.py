import re
from faker_engine.generators.leafs.date import DateGenerator
from faker_engine.generators.leafs.datetime import DateTimeGenerator
from faker_engine.generators.leafs.timestamp import TimestampGenerator
from faker_engine.context import GenContext


def test_date_iso_default_range():
    ctx = GenContext(seed=2)
    gen = DateGenerator()
    out = gen.generate(ctx)
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", out)


def test_date_epoch_ms():
    ctx = GenContext(seed=2)
    gen = DateGenerator(format='epoch_ms')
    out = gen.generate(ctx)
    assert isinstance(out, int)


def test_datetime_iso_second_precision():
    ctx = GenContext(seed=9)
    gen = DateTimeGenerator()
    out = gen.generate(ctx)
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", out)


def test_timestamp_units():
    ctx = GenContext(seed=4)
    ms = TimestampGenerator(unit='ms').generate(ctx)
    us = TimestampGenerator(unit='us').generate(ctx)
    assert isinstance(ms, int) and isinstance(us, int)
    assert ms >= 0 and us >= 0
