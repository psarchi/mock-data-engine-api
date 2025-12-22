from __future__ import annotations

import importlib
import pytest


from tests.core.chaos.utils import get_all_registered_chaos_ops


@pytest.mark.skip(reason="burst chaos op test pending")
def test_all_chaos_ops_have_tests():
    missing = []
    for op in get_all_registered_chaos_ops():
        mod_name = f"tests.core.chaos.test_{op}"
        try:
            mod = importlib.import_module(mod_name)
        except ImportError:
            missing.append(f"{op} (missing module)")
            continue

        streaming_func = getattr(mod, f"test_{op}_streaming", None)
        rest_func = getattr(mod, f"test_{op}_rest", None)
        if not streaming_func and not rest_func:
            missing.append(f"{op} (no streaming/rest test function)")

    assert not missing, f"Chaos ops missing tests: {', '.join(missing)}"
