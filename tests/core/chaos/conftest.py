import os
import time

import pytest
import requests

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
SCHEMA = os.getenv("SCHEMA", "smoke")
TIMEOUT = float(os.getenv("TIMEOUT", "15.0"))


def pytest_collection_modifyitems(session, config, items):
    """Mark all chaos tests as integration so they are skipped in CI by default."""
    for item in items:
        if "tests/core/chaos" in str(item.fspath):
            item.add_marker(pytest.mark.integration)


def _op_name_from_request(request) -> str:
    name = request.node.name
    if name.startswith("test_"):
        name = name[len("test_") :]
    for suffix in ("_streaming", "_rest"):
        if name.endswith(suffix):
            name = name[: -len(suffix)]
    return name


@pytest.fixture
def op_name(request) -> str:
    return _op_name_from_request(request)


def _fetch(schema: str, chaos: str | None = None):
    params = {"count": 3, "include_metadata": "true"}
    if chaos:
        params["chaos_ops"] = chaos
    resp = requests.get(
        f"{BASE_URL}/v1/schemas/{schema}/generate", params=params, timeout=TIMEOUT
    )
    return resp


@pytest.fixture
def baseline_items():
    resp = _fetch(SCHEMA, chaos=None)
    resp.raise_for_status()
    data = resp.json()
    return data.get("items", [])


@pytest.fixture
def chaos_response(op_name):
    start = time.time()
    resp = _fetch(SCHEMA, chaos=op_name)
    elapsed = time.time() - start
    return resp, elapsed


@pytest.fixture
def chaos_items(chaos_response):
    resp, _ = chaos_response
    try:
        resp.raise_for_status()
        data = resp.json()
        return data.get("items", [])
    except Exception:
        return []


@pytest.fixture
def chaos_applied(chaos_response):
    resp, _ = chaos_response
    try:
        data = resp.json()
        meta = data.get("_metadata", {})
        applied = meta.get("chaos_applied", []) if isinstance(meta, dict) else []
        if not applied:
            applied = data.get("chaos_applied", [])
        return applied or []
    except Exception:
        return []


@pytest.fixture
def status_code(chaos_response):
    resp, _ = chaos_response
    return getattr(resp, "status_code", None)


@pytest.fixture
def baseline_elapsed():
    return 0.05


@pytest.fixture
def chaos_elapsed(chaos_response):
    _, elapsed = chaos_response
    return elapsed
