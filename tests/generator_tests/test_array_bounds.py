from pathlib import Path

from mock_engine import api as engine_api
from mock_engine.context import GenContext
from mock_engine.schema.builder import build_schema
from mock_engine.schema.registry import SchemaRegistry


def test_array_bounds_pipeline():
    schema_name = "array_fixture"
    schema_path = Path(__file__).resolve().parents[1] / "schemas" / "array.yaml"

    doc = build_schema(schema_name, schema_path.read_text(), source_path=str(schema_path))
    SchemaRegistry.register(schema_name, doc)

    gen = engine_api.build(doc.contracts_by_path)
    ctx = GenContext(seed=42)
    obj = gen.generate(ctx)
    arr = obj["arr"]

    assert isinstance(arr, list)
    assert 1 <= len(arr) <= 3
    assert all(isinstance(x, bool) for x in arr)
