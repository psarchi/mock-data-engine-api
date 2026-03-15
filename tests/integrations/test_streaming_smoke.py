import importlib
from typing import Any, Dict

import pytest

pytestmark = pytest.mark.skip(reason="WebSocket streaming tests require a running pregen worker; not suitable for CI")


def test_basic_generation(ws_baseline):
    """Test basic generation without chaos returns valid smoke.yaml data."""
    items = ws_baseline["items"]
    assert len(items) >= 1, f"Expected at least 1 item, got {len(items)}"

    for item in items:
        assert isinstance(item, dict), f"Item is not a dict: {type(item)}"
        _validate_smoke_schema(item)


def test_chaos_ops(chaos_op, ws_baseline, ws_chaos):
    """Test each chaos op applies correctly via WebSocket endpoint.

    This test is parametrized to run for all 18 chaos ops.
    It imports the corresponding test function from tests/core/chaos/test_<op>.py
    and verifies the chaos op behaves as expected.
    """
    module_name = f"tests.core.chaos.test_{chaos_op}"
    test_func_name = f"test_{chaos_op}_streaming"

    try:
        module = importlib.import_module(module_name)
        test_func = getattr(module, test_func_name)
    except (ImportError, AttributeError) as e:
        raise AssertionError(
            f"Could not import {test_func_name} from {module_name}: {e}"
        )

    chaos_result = ws_chaos(chaos_op)

    baseline_items = ws_baseline["items"]
    chaos_items = chaos_result["items"]
    chaos_applied = chaos_result["chaos_applied"]

    import inspect

    sig = inspect.signature(test_func)
    kwargs = {}

    if "baseline_elapsed" in sig.parameters:
        kwargs["baseline_elapsed"] = ws_baseline["elapsed"]
    if "chaos_elapsed" in sig.parameters:
        kwargs["chaos_elapsed"] = chaos_result["elapsed"]

    passed, data = test_func(
        baseline_items=baseline_items,
        chaos_items=chaos_items,
        chaos_applied=chaos_applied,
        **kwargs,
    )

    assert passed, f"Test failed for {chaos_op}: {data}"


def test_schema_validation(ws_baseline):
    """Test that generated data conforms to smoke.yaml schema structure."""
    items = ws_baseline["items"]

    for idx, item in enumerate(items):
        try:
            _validate_smoke_schema(item)
        except AssertionError as e:
            raise AssertionError(f"Item {idx} failed validation: {e}")


def _validate_smoke_schema(item: Dict[str, Any]):
    """Validate that item conforms to smoke.yaml schema structure.

    Checks for required fields and their types based on smoke.yaml.
    """
    required_fields = {
        "int_field": int,
        "float_field": (int, float),
        "bool_field": bool,
        "string_template": str,
        "string_regex": str,
        "enum_field": str,
        "array_field": list,
        "object_field": dict,
        "timestamp_field": (int, float),
        "datetime_field": str,
        "stateful_timestamp_field": (int, float),
        "stateful_datetime_field": str,
    }

    optional_fields = {
        "maybe_field": (str, type(None)),
        "one_of_field": (int, str),
        "select_field": dict,
        "string_or_null_field": (str, type(None)),
    }

    for field_name, expected_types in required_fields.items():
        assert field_name in item, f"Missing required field: {field_name}"
        value = item[field_name]

        if not isinstance(expected_types, tuple):
            expected_types = (expected_types,)

        assert isinstance(value, expected_types), (
            f"Field '{field_name}' has wrong type: expected {expected_types}, "
            f"got {type(value).__name__} (value: {value})"
        )

    for field_name, expected_types in optional_fields.items():
        if field_name in item:
            value = item[field_name]
            if not isinstance(expected_types, tuple):
                expected_types = (expected_types,)

            assert isinstance(value, expected_types), (
                f"Field '{field_name}' has wrong type: expected {expected_types}, "
                f"got {type(value).__name__} (value: {value})"
            )

    if "object_field" in item:
        obj = item["object_field"]
        assert "nested_id" in obj, "object_field missing nested_id"
        assert isinstance(obj["nested_id"], int), "nested_id should be int"
        assert "nested_flag" in obj, "object_field missing nested_flag"
        assert isinstance(obj["nested_flag"], bool), "nested_flag should be bool"
        assert "nested_list" in obj, "object_field missing nested_list"
        assert isinstance(obj["nested_list"], list), "nested_list should be list"

        for nested_val in obj["nested_list"]:
            assert isinstance(nested_val, float), (
                f"nested_list item should be float, got {type(nested_val)}"
            )

    if "enum_field" in item:
        assert item["enum_field"] in ["alpha", "beta", "gamma"], (
            f"enum_field has invalid value: {item['enum_field']}"
        )
