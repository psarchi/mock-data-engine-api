from pathlib import Path

from mock_engine import api as engine_api
from mock_engine.context import GenContext
from mock_engine.schema.builder import build_schema
from mock_engine.schema.registry import SchemaRegistry

def test_object_fields_present_and_types():
    schema_name = "object_basic_fixture"
    schema_path = Path(__file__).resolve().parents[1] / "schemas" / "object_basic.yaml"
    doc = build_schema(schema_name, schema_path.read_text(), source_path=str(schema_path))
    SchemaRegistry.register(schema_name, doc)

    gen = engine_api.build(doc.contracts_by_path)
    obj = gen.generate(GenContext(seed=7))["obj"]
    assert set(obj.keys()) == {"id", "ok", "label"}
    assert isinstance(obj["ok"], bool)
    assert isinstance(obj["label"], str) and len(obj["label"]) > 0
    assert 1 <= obj["id"] <= 5
