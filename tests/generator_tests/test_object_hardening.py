from pathlib import Path

import pytest
import yaml

from mock_engine import api as engine_api
from mock_engine.context import GenContext
from mock_engine.generators.errors import InvalidParameterError


def test_object_required_raises_on_none():
    schema_path = Path(__file__).resolve().parents[1] / "schemas" / "object_required_fail.yaml"
    spec = yaml.safe_load(schema_path.read_text())
    gen = engine_api.build_generator(spec)
    ctx = GenContext(seed=1)
    with pytest.raises(InvalidParameterError):
        gen.generate(ctx)


def test_object_default_applied():
    schema_path = Path(__file__).resolve().parents[1] / "schemas" / "object_default_applied.yaml"
    spec = yaml.safe_load(schema_path.read_text())
    gen = engine_api.build_generator(spec)
    ctx = GenContext(seed=1)
    out = gen.generate(ctx)["rec"]
    assert out == {"defaulted_null": 7, "b": 2}
