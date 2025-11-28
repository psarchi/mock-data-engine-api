import re
from pathlib import Path

from mock_engine import api as engine_api
from mock_engine.context import GenContext
from mock_engine.generators.leafs.string import StringGenerator
from mock_engine.schema.builder import build_schema
from mock_engine.schema.registry import SchemaRegistry


def test_string_pipeline(monkeypatch):
    schema_name = "string_fixture"
    schema_path = Path(__file__).resolve().parents[1] / "schemas" / "string.yaml"
    doc = build_schema(schema_name, schema_path.read_text(), source_path=str(schema_path))
    SchemaRegistry.register(schema_name, doc)

    monkeypatch.setattr(StringGenerator, "_resolve_faker_provider", lambda self, st, c: (lambda: "Alice"))

    gen = engine_api.build(doc.contracts_by_path)
    out = gen.generate(GenContext(seed=7))
    assert out["template_upper"].startswith("ISO-") and re.fullmatch(r"ISO-[A-Z]{3}", out["template_upper"])
    assert re.fullmatch(r"ID-[0-9]{2}", out["template_numeric"])
    regex_out = out["regex_plain"]
    assert re.fullmatch(r"^[a-z0-9]{8}$", regex_out)

    assert out["faker_name"] == "Alice"
