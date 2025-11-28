from pathlib import Path

import yaml

from mock_engine import api as engine_api
from mock_engine.context import GenContext


def test_enum_weights_bias():
    schema_path = Path(__file__).resolve().parents[1] / "schemas" / "enum.yaml"
    spec = yaml.safe_load(schema_path.read_text())
    gen = engine_api.build_generator(spec)
    ctx = GenContext(seed=3)
    out = gen.generate(ctx)["bias"]
    if isinstance(out, dict):
        assert out.get("type") == "y"
    else:
        assert out == "y"
