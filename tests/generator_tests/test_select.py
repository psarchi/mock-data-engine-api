from pathlib import Path

import yaml

from mock_engine import api as engine_api
from mock_engine.context import GenContext


def test_select_required_and_exact():
    schema_path = Path(__file__).resolve().parents[1] / "schemas" / "select.yaml"
    spec = yaml.safe_load(schema_path.read_text())
    gen = engine_api.build_generator(spec)
    out = gen.generate(GenContext(seed=9))["selection"]
    assert "req" in out and len(out) == 2 and set(out.keys()).issubset({"req", "opt1", "opt2"})
