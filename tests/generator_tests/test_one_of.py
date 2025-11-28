from pathlib import Path

from mock_engine import api as engine_api
from mock_engine.context import GenContext
from mock_engine.schema.builder import build_schema
from mock_engine.schema.registry import SchemaRegistry


def test_one_of_pipeline():
    schema_name = "one_of_fixture"
    schema_path = Path(__file__).resolve().parents[1] / "schemas" / "one_of.yaml"
    doc = build_schema(schema_name, schema_path.read_text(), source_path=str(schema_path))
    SchemaRegistry.register(schema_name, doc)

    gen = engine_api.build(doc.contracts_by_path)
    ctx = GenContext(seed=1)
    out = gen.generate(ctx)
    assert out["choice_uniform"] in ("A", "B")
    assert out["choice_weighted"] == "B"
