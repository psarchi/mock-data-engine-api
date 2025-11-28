import re
from pathlib import Path

from mock_engine import api as engine_api
from mock_engine.context import GenContext
from mock_engine.schema.builder import build_schema
from mock_engine.schema.registry import SchemaRegistry


def test_time_generators_pipeline():
    schema_name = "time_fixture"
    schema_path = Path(__file__).resolve().parents[1] / "schemas" / "time.yaml"
    doc = build_schema(schema_name, schema_path.read_text(), source_path=str(schema_path))
    SchemaRegistry.register(schema_name, doc)

    gen = engine_api.build(doc.contracts_by_path)

    date_out = gen.generate(GenContext(seed=2))["date_iso"]
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_out)

    ts = gen.generate(GenContext(seed=2))["timestamp_us"]
    assert isinstance(ts, int) and ts >= 0

    dt_out = gen.generate(GenContext(seed=9))["datetime_iso"]
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", dt_out)
