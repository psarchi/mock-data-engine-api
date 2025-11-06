
from mock_engine.api import build_generator, generate_one

def test_array_bounds():
    spec = {
        "type": "array",
        "min_items": 1,
        "max_items": 3,
        "child": {"type": "bool"}
    }
    gen = build_generator(spec)
    arr = generate_one(gen, seed=42, locale="en_US")
    assert isinstance(arr, list)
    assert 1 <= len(arr) <= 3
    assert all(isinstance(x, bool) for x in arr)
