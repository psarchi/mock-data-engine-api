import os
import time
from typing import Any

import pytest
import requests
import websocket

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
WS_URL = os.getenv("WS_URL", "ws://localhost:8000")
SCHEMA = "smoke"
TIMEOUT = float(os.getenv("TIMEOUT", "15.0"))


def pytest_collection_modifyitems(session, config, items):
    """Mark all integration tests so they can be run with -m integration."""
    for item in items:
        if "tests/integrations" in str(item.fspath):
            item.add_marker(pytest.mark.integration)


@pytest.fixture
def base_url():
    """Base URL for REST API."""
    return BASE_URL


@pytest.fixture
def ws_url():
    """Base URL for WebSocket API."""
    return WS_URL


@pytest.fixture
def schema_name():
    """Schema name to test against."""
    return SCHEMA


@pytest.fixture
def timeout():
    """Request timeout."""
    return TIMEOUT


@pytest.fixture
def rest_fetch(base_url, schema_name, timeout):
    """Factory to fetch from REST endpoint."""

    def _fetch(chaos: str | None = None, count: int = 3):
        params = {"count": count, "include_metadata": "true"}
        if chaos is None:
            params["chaos_ops"] = "none"
        if chaos:
            params["chaos_ops"] = chaos
        start = time.time()
        resp = requests.get(
            f"{base_url}/v1/schemas/{schema_name}/generate",
            params=params,
            timeout=timeout,
        )
        elapsed = time.time() - start
        return resp, elapsed

    return _fetch


@pytest.fixture
def rest_baseline(rest_fetch):
    """Fetch baseline items without chaos."""
    resp, elapsed = rest_fetch(chaos=None)
    resp.raise_for_status()
    data = resp.json()
    return {
        "items": data.get("items", []),
        "elapsed": elapsed,
        "metadata": data.get("_metadata", {}),
    }


@pytest.fixture
def rest_chaos(rest_fetch):
    """Factory to fetch items with specific chaos op."""

    def _fetch_chaos(op_name: str):
        resp, elapsed = rest_fetch(chaos=op_name)
        status_code = getattr(resp, "status_code", None)

        items = []
        metadata: dict[str, Any] = {}
        chaos_applied: list[str] = []
        error: str | None = None

        try:
            data = resp.json()
            if isinstance(data, dict):
                items = data.get("items", []) or []
                metadata = data.get("_metadata", {}) or {}
                chaos_applied = (
                    metadata.get("chaos_applied", [])
                    if isinstance(metadata, dict)
                    else []
                )
                if not chaos_applied:
                    chaos_applied = data.get("chaos_applied", []) or []
        except Exception as exc:
            error = str(exc)

        return {
            "items": items,
            "elapsed": elapsed,
            "chaos_applied": chaos_applied,
            "status_code": status_code,
            "metadata": metadata,
            "error": error,
        }

    return _fetch_chaos


@pytest.fixture
def ws_connect(ws_url, schema_name, timeout):
    """Factory to create WebSocket connections."""

    def _connect(chaos: str | None = None, count: int = 3):
        params = f"count={count}&include_metadata=true"
        if chaos is None:
            params += "&forced_chaos=none"
        if chaos:
            params += f"&forced_chaos={chaos}"

        url = f"{ws_url}/v1/schemas/{schema_name}/stream?{params}"
        ws = websocket.create_connection(url, timeout=timeout)
        return ws

    return _connect


@pytest.fixture
def ws_fetch(ws_connect):
    """Factory to fetch items via WebSocket."""

    def _fetch(chaos: str | None = None, count: int = 3):
        ws = ws_connect(chaos=chaos, count=count)
        items = []
        chaos_applied = []
        metadata = {}

        try:
            start = time.time()
            while True:
                try:
                    msg = ws.recv()
                    if not msg:
                        break

                    import json

                    data = json.loads(msg)

                    if isinstance(data, dict):
                        msg_type = data.get("type")

                        if msg_type == "start":
                            continue

                        if msg_type == "event":
                            if "data" in data:
                                items.append(data["data"])

                            if "chaos_applied" in data:
                                chaos_applied = data["chaos_applied"]
                            if "chaos_meta" in data:
                                metadata["chaos_meta"] = data["chaos_meta"]

                        elif "items" in data:
                            items.extend(data["items"])
                        elif "item" in data:
                            items.append(data["item"])

                    if len(items) >= count:
                        break

                except websocket.WebSocketTimeoutException:
                    break

            elapsed = time.time() - start

            return {
                "items": items,
                "elapsed": elapsed,
                "chaos_applied": chaos_applied,
                "metadata": metadata,
            }
        finally:
            ws.close()

    return _fetch


@pytest.fixture
def ws_baseline(ws_fetch):
    """Fetch baseline items via WebSocket without chaos."""
    return ws_fetch(chaos=None)


@pytest.fixture
def ws_chaos(ws_fetch):
    """Factory to fetch items via WebSocket with specific chaos op."""

    def _fetch_chaos(op_name: str):
        return ws_fetch(chaos=op_name)

    return _fetch_chaos


CHAOS_OPS = [
    "auth_fault",
    "burst",
    "data_drift",
    "duplicate_items",
    "encoding_corrupt",
    "header_anomaly",
    "http_error",
    "http_mismatch",
    "late_arrival",
    "latency",
    "list_shuffle",
    "partial_load",
    "random_header_case",
    "schema_bloat",
    "schema_drift",
    "schema_field_nulling",
    "schema_time_skew",
    "time_skew",
    "truncate",
]


@pytest.fixture(params=CHAOS_OPS)
def chaos_op(request):
    """Parametrized fixture providing each chaos op name."""
    return request.param
