from pathlib import Path

from mock_engine import api as engine_api
from mock_engine.context import GenContext
from mock_engine.schema.builder import build_schema
from mock_engine.schema.registry import SchemaRegistry


def test_bool_deterministic_sequence():
    schema_name = "bool_fixture"
    schema_path = Path(__file__).resolve().parents[1] / "schemas" / "bool.yaml"
    doc = build_schema(schema_name, schema_path.read_text(), source_path=str(schema_path))
    SchemaRegistry.register(schema_name, doc)

    gen = engine_api.build(doc.contracts_by_path)
    ctx1 = GenContext(seed=123)
    ctx2 = GenContext(seed=123)
    seq1 = [gen.generate(ctx1)["flag"] for _ in range(20)]
    seq2 = [gen.generate(ctx2)["flag"] for _ in range(20)]
    assert seq1 == seq2
    assert all(isinstance(x, bool) for x in seq1)
