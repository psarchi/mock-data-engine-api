from pathlib import Path

import yaml

from mock_engine import api as engine_api
from mock_engine.context import GenContext


def test_object_or_null_all_null():
    schema_path = Path(__file__).resolve().parents[1] / "schemas" / "object_or_null.yaml"
    spec = yaml.safe_load(schema_path.read_text())
    gen = engine_api.build_generator(spec)
    ctx = GenContext(seed=42)
    out = gen.generate(ctx)
    assert out["always_obj"] == {"id": 1}
    assert out["always_null"] in (None, {"id": 1})
