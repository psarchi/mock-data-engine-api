from pathlib import Path

from mock_engine import api as engine_api
from mock_engine.context import GenContext
from mock_engine.schema.builder import build_schema
from mock_engine.schema.registry import SchemaRegistry

def test_int_step_progression():
    schema_name = "numbers_fixture"
    schema_path = Path(__file__).resolve().parents[1] / "schemas" / "numbers.yaml"
    doc = build_schema(schema_name, schema_path.read_text(), source_path=str(schema_path))
    SchemaRegistry.register(schema_name, doc)

    gen = engine_api.build(doc.contracts_by_path)
    ctx = GenContext(seed=5)
    val = gen.generate(ctx)["step_int"]
    assert val in {0, 5, 10}


def test_float_precision():
    schema_name = "numbers_fixture"
    schema_path = Path(__file__).resolve().parents[1] / "schemas" / "numbers.yaml"
    doc = build_schema(schema_name, schema_path.read_text(), source_path=str(schema_path))
    SchemaRegistry.register(schema_name, doc)

    gen = engine_api.build(doc.contracts_by_path)
    ctx = GenContext(seed=1)
    val = gen.generate(ctx)["precise_float"]
    assert isinstance(val, float)
    s = f"{val:.3f}"
    assert len(s.split(".")[1]) == 3
