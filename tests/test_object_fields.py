from faker_engine.api import build_generator, generate_one

def test_object_fields_present_and_types():
    spec = {
        "type": "object",
        "fields": {
            "id": {"type": "int", "min": 1, "max": 5},
            "ok": {"type": "bool"},
            "label": {"type": "string", "string_type": "word"}
        }
    }
    gen = build_generator(spec)
    obj = generate_one(gen, seed=7, locale="en_US")
    assert set(obj.keys()) == {"id", "ok", "label"}
    assert isinstance(obj["ok"], bool)
    assert isinstance(obj["label"], str) and len(obj["label"]) > 0
    assert 1 <= obj["id"] <= 5
