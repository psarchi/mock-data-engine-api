from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

# Add repo root to path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest
from tests.core.generators.utils import get_all_registered_generators

pytestmark = pytest.mark.skip(reason="Aggregator script; run manually if needed")

COUNT = int(__import__("os").getenv("COUNT", "100"))
SEED = (
    int(__import__("os").getenv("SEED", "12345"))
    if __import__("os").getenv("SEED")
    else None
)


class TestResult:
    """Test result container."""

    def __init__(self, name: str):
        self.name = name
        self.passed = False
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.data: Dict[str, Any] = {}

    def add_error(self, msg: str):
        self.errors.append(msg)
        self.passed = False

    def add_warning(self, msg: str):
        self.warnings.append(msg)

    def set_passed(self):
        self.passed = True

    def __str__(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        msg = f"{status} {self.name}"
        if self.errors:
            msg += f"\n   Errors: {', '.join(self.errors)}"
        if self.warnings:
            msg += f"\n   Warnings: {', '.join(self.warnings)}"
        return msg


def get_generator_test_function(gen_name: str) -> Optional[Callable]:
    """Get the test function for a generator.

    Handles aliases and stateful generators.
    """
    alias_map = {
        "str": "string",
        "list": "array",
        "timestamp_stateful": "stateful_timestamp",
        "ts_stateful": "stateful_timestamp",
        "datetime_stateful": "stateful_datetime",
        "dt_stateful": "stateful_datetime",
    }

    canonical_name = alias_map.get(gen_name, gen_name)

    test_name_map = {
        "int": "test_int",
        "float": "test_float",
        "bool": "test_bool",
        "string": "test_string",
        "str": "test_string",
        "array": "test_array",
        "list": "test_array",
        "enum": "test_enum",
        "maybe": "test_maybe",
        "object": "test_object",
        "object_or_null": "test_object_or_null",
        "one_of": "test_one_of",
        "select": "test_select",
        "timestamp": "test_timestamp",
        "datetime": "test_datetime",
        "string_or_null": "test_string_or_null",
        "stateful_timestamp": "test_stateful_timestamp",
        "timestamp_stateful": "test_stateful_timestamp",
        "ts_stateful": "test_stateful_timestamp",
        "stateful_datetime": "test_stateful_datetime",
        "datetime_stateful": "test_stateful_datetime",
        "dt_stateful": "test_stateful_datetime",
    }

    func_name_variations = {
        "stateful_timestamp": "test_stateful_timestamp_generator",
        "timestamp_stateful": "test_stateful_timestamp_generator",
        "ts_stateful": "test_stateful_timestamp_generator",
        "stateful_datetime": "test_stateful_datetime_generator",
        "datetime_stateful": "test_stateful_datetime_generator",
        "dt_stateful": "test_stateful_datetime_generator",
    }

    test_module_name = test_name_map.get(canonical_name)
    if not test_module_name:
        return None

    module_name = f"tests.core.generators.{test_module_name}"
    try:
        module = importlib.import_module(module_name)
        func_name = func_name_variations.get(canonical_name)
        if func_name:
            func = getattr(module, func_name, None)
            if func:
                return func
        func = getattr(module, f"test_{canonical_name}_generator", None)
        if func:
            return func
        func = getattr(
            module, f"test_{test_module_name.replace('test_', '')}_generator", None
        )
        return func
    except ImportError:
        return None


def test_generator(gen_name: str) -> TestResult:
    """Test a single generator using its test function."""
    result = TestResult(f"Generator: {gen_name}")

    try:
        test_func = get_generator_test_function(gen_name)
        if not test_func:
            result.add_error(f"No test function found for {gen_name}")
            return result

        passed, data = test_func(count=COUNT, seed=SEED)

        if passed:
            result.set_passed()
            result.data = data
        else:
            result.add_error(f"Test failed: {data}")

    except Exception as e:
        result.add_error(f"Exception: {e}")

    return result


def run_all_tests():
    """Run all tests and report results."""
    print("Testing Generators")
    print(f"   Count per test: {COUNT}")
    print(f"   Seed: {SEED if SEED else 'random'}")
    print()

    all_gens = get_all_registered_generators()
    print(f"Found {len(all_gens)} registered generators: {', '.join(all_gens)}")
    print()

    missing_tests = []
    for gen_name in all_gens:
        test_func = get_generator_test_function(gen_name)
        if not test_func:
            missing_tests.append(gen_name)

    if missing_tests:
        print(f"WARNING: Missing tests for generators: {', '.join(missing_tests)}")
        print()

    results = []
    for gen_name in all_gens:
        if gen_name not in missing_tests:
            result = test_generator(gen_name)
            results.append(result)
            print(result)
            if result.data:
                print(f"   Data: {result.data}")
            print()

    # Summary
    passed = sum(1 for r in results if r.passed)
    total = len(results)

    print("=" * 60)
    print(f"Summary: {passed}/{total} tests passed")
    if missing_tests:
        print(f"Missing tests: {len(missing_tests)} generators")
    print("=" * 60)

    if passed == total:
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
