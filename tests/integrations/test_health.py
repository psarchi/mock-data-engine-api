"""Integration tests for health check endpoints."""

import pytest
import requests


def test_health_basic(base_url, timeout):
    """Test basic /v1/health endpoint returns ok status."""
    resp = requests.get(f"{base_url}/v1/health", timeout=timeout)
    resp.raise_for_status()

    data = resp.json()
    assert data["status"] == "ok", f"Expected status 'ok', got {data['status']}"
    assert "ts" in data, "Missing timestamp field"


def test_health_live(base_url, timeout):
    """Test /v1/health/live liveness probe."""
    resp = requests.get(f"{base_url}/v1/health/live", timeout=timeout)
    resp.raise_for_status()

    data = resp.json()
    assert data["status"] == "ok", f"Expected status 'ok', got {data['status']}"
    assert "ts" in data, "Missing timestamp field"


def test_health_ready(base_url, timeout):
    """Test /v1/health/ready readiness probe checks dependencies."""
    resp = requests.get(f"{base_url}/v1/health/ready", timeout=timeout)

    # Readiness check returns 200 if healthy, 503 if not ready
    assert resp.status_code in [200, 503], (
        f"Expected status 200 or 503, got {resp.status_code}"
    )

    data = resp.json()
    assert "status" in data, "Missing status field"
    assert "checks" in data, "Missing checks field"
    assert "ts" in data, "Missing timestamp field"

    # Verify checks structure
    checks = data["checks"]
    assert "redis" in checks, "Missing redis check"
    assert "postgres" in checks, "Missing postgres check"

    # If status is ready, all checks should be healthy
    if data["status"] == "ready":
        assert resp.status_code == 200, "Ready status should return 200"
        assert checks["redis"] == "healthy", f"Redis check failed: {checks['redis']}"
        assert checks["postgres"] == "healthy", f"Postgres check failed: {checks['postgres']}"

    # If status is not_ready, at least one check should be unhealthy
    if data["status"] == "not_ready":
        assert resp.status_code == 503, "Not ready status should return 503"
        assert (
            checks["redis"] != "healthy" or checks["postgres"] != "healthy"
        ), "Not ready status but all checks healthy"
