import json
from mock_engine.api import build_generator, generate_many, MockEngine


def main():
    # ---------------- Functional API demo ----------------
    print("=== Functional API ===")
    spec = {
        "type": "array",
        "min_items": 2,
        "max_items": 3,
        "child": {
            "type": "object",
            "fields": {
                "id": {"type": "int", "min_value": 1, "max_value": 10},
                "name": {"type": "string", "string_type": "name"},
                "active": {"type": "bool"},
            },
        },
    }

    gen = build_generator(spec)
    records = generate_many(gen, n=3, seed=123, locale="en_US")
    for rec in records:
        print(json.dumps(rec, ensure_ascii=False))

    print("\n" + "=" * 60 + "\n")

    # ---------------- OOP API demo ----------------
    print("=== OOP API ===")
    engine = MockEngine(seed=123, locale="en_US")
    gen = engine.build(spec)
    records = engine.generate_many(gen, n=3)
    for rec in records:
        print(json.dumps(rec, ensure_ascii=False))


if __name__ == "__main__":
    main()
