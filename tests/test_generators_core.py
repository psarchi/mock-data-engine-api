"""Single-entry generator suite that parametrizes all generator test cases."""

import importlib
import inspect

import pytest


MODULES = [
    "tests.generator_tests.test_int_range",
    "tests.generator_tests.test_int_float",
    "tests.generator_tests.test_array_bounds",
    "tests.generator_tests.test_object_fields",
    "tests.generator_tests.test_object_hardening",
    "tests.generator_tests.test_object_or_null",
    "tests.generator_tests.test_maybe",
    "tests.generator_tests.test_one_of",
    "tests.generator_tests.test_select",
    "tests.generator_tests.test_string_paths",
    "tests.generator_tests.test_enum_weights",
    "tests.generator_tests.test_bool_determinism",
    "tests.generator_tests.test_time_generators",
]


def _collect_cases():
    for mod_name in MODULES:
        mod = importlib.import_module(mod_name)
        for attr in dir(mod):
            if not attr.startswith("test_"):
                continue
            fn = getattr(mod, attr)
            if callable(fn):
                yield pytest.param(fn, id=f"{mod_name}.{attr}")


@pytest.mark.parametrize("case_fn", list(_collect_cases()))
def test_generators_core(case_fn, monkeypatch):
    sig = inspect.signature(case_fn)
    if "monkeypatch" in sig.parameters:
        case_fn(monkeypatch)
    else:
        case_fn()
