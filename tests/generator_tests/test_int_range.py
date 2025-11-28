from pathlib import Path

from mock_engine import api as engine_api
from mock_engine.context import GenContext
from mock_engine.schema.builder import build_schema
from mock_engine.schema.registry import SchemaRegistry

def test_int_within_bounds():
    schema_name = "int_fixture"
    schema_path = Path(__file__).resolve().parents[1] / "schemas" / "int.yaml"
    doc = build_schema(schema_name, schema_path.read_text(), source_path=str(schema_path))
    SchemaRegistry.register(schema_name, doc)

    gen = engine_api.build(doc.contracts_by_path)
    ctx = GenContext(seed=123)
    for _ in range(100):
        v = gen.generate(ctx)["num"]
        assert 1 <= v <= 5
