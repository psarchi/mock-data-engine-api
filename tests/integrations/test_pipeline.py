"""Integration tests for streaming pipeline (metadata, logging, observability)."""

import pytest
import requests


@pytest.mark.integration
def test_metadata_enabled(base_url, schema_name, timeout):
    """Test that metadata is included when enabled via include_metadata param."""
    endpoint = f"{base_url}/v1/schemas/{schema_name}/generate"
    
    # Request with metadata enabled
    resp = requests.get(
        endpoint,
        params={"count": 5, "include_metadata": "true"},
        timeout=timeout
    )
    resp.raise_for_status()
    data = resp.json()
    
    # Verify metadata field is present
    assert "_metadata" in data, "Expected _metadata field when include_metadata=true"
    
    metadata = data["_metadata"]
    assert "seed" in metadata, "Expected seed in metadata"
    assert "schema" in metadata, "Expected schema in metadata"
    
    # Verify items are present
    assert "items" in data, "Expected items in response"
    assert len(data["items"]) == 5, "Expected 5 items"


@pytest.mark.integration
def test_metadata_disabled(base_url, schema_name, timeout):
    """Test that metadata is excluded when include_metadata is false."""
    endpoint = f"{base_url}/v1/schemas/{schema_name}/generate"
    
    # Request without metadata (default behavior)
    resp = requests.get(
        endpoint,
        params={"count": 5, "include_metadata": "false"},
        timeout=timeout
    )
    resp.raise_for_status()
    data = resp.json()
    
    # Verify metadata field is NOT present
    assert "_metadata" not in data, "Expected no _metadata field when include_metadata=false"
    
    # Verify items are still present
    assert "items" in data, "Expected items in response"
    assert len(data["items"]) == 5, "Expected 5 items"


@pytest.mark.integration
def test_observability_metrics(base_url, schema_name, timeout):
    """Test that Prometheus metrics are exported correctly."""
    # Generate some data to produce metrics
    endpoint = f"{base_url}/v1/schemas/{schema_name}/generate"
    
    for _ in range(3):
        resp = requests.get(endpoint, params={"count": 10}, timeout=timeout)
        resp.raise_for_status()
    
    # Query metrics endpoint
    metrics_resp = requests.get(f"{base_url}/metrics", timeout=timeout)
    metrics_resp.raise_for_status()
    
    metrics_text = metrics_resp.text
    
    # Verify expected metrics are present
    expected_metrics = [
        "items_generated_total",
        "generation_duration_seconds",
        "seed_source_total",
    ]
    
    for metric in expected_metrics:
        assert metric in metrics_text, f"Expected metric '{metric}' not found in /metrics"
    
    # Verify metric has schema label
    assert f'schema="{schema_name}"' in metrics_text or f"schema=\"{schema_name}\"" in metrics_text, \
        f"Expected schema label '{schema_name}' in metrics"


@pytest.mark.integration
def test_dynamic_config_update(base_url, timeout):
    """Test that configuration can be queried and updated dynamically."""
    # Query current server config
    config_resp = requests.get(
        f"{base_url}/v1/admin/config/server",
        timeout=timeout
    )
    config_resp.raise_for_status()
    original_config = config_resp.json()
    
    assert "admin" in original_config, "Expected admin config"
    assert "enabled" in original_config["admin"], "Expected admin.enabled field"
    
    # Update config in-memory (non-persistent)
    original_value = original_config["admin"]["enabled"]
    new_value = not original_value
    
    update_resp = requests.post(
        f"{base_url}/v1/admin/config/server/update",
        json={"admin.enabled": new_value},
        timeout=timeout
    )
    update_resp.raise_for_status()
    update_result = update_resp.json()
    
    assert update_result["success"], "Expected successful config update"
    assert "admin.enabled" in update_result["updates"]
    
    # Verify config was updated
    updated_config_resp = requests.get(
        f"{base_url}/v1/admin/config/server",
        timeout=timeout
    )
    updated_config_resp.raise_for_status()
    updated_config = updated_config_resp.json()
    
    assert updated_config["admin"]["enabled"] == new_value, \
        "Expected config value to be updated"
    
    # Restore original value
    restore_resp = requests.post(
        f"{base_url}/v1/admin/config/server/update",
        json={"admin.enabled": original_value},
        timeout=timeout
    )
    restore_resp.raise_for_status()


@pytest.mark.integration
def test_chaos_metadata_reporting(base_url, schema_name, timeout):
    """Test that chaos operations are reported in metadata."""
    endpoint = f"{base_url}/v1/schemas/{schema_name}/generate"
    
    # Request with chaos op and metadata
    resp = requests.get(
        endpoint,
        params={
            "count": 5,
            "chaos_ops": "list_shuffle",
            "include_metadata": "true"
        },
        timeout=timeout
    )
    resp.raise_for_status()
    data = resp.json()
    
    # Verify metadata contains chaos information
    assert "_metadata" in data, "Expected _metadata field"
    metadata = data["_metadata"]
    
    assert "chaos_applied" in metadata, "Expected chaos_applied in metadata"
    chaos_applied = metadata["chaos_applied"]
    
    # Verify chaos op was applied (should be list of descriptions)
    if chaos_applied:
        assert isinstance(chaos_applied, list), "Expected chaos_applied to be a list"
        assert len(chaos_applied) > 0, "Expected at least one chaos op description"
        assert any("list_shuffle" in desc.lower() for desc in chaos_applied), \
            "Expected list_shuffle chaos op in descriptions"


@pytest.mark.integration
def test_end_to_end_pipeline(base_url, schema_name, timeout):
    """Test complete pipeline with metadata and observability.
    
    This test verifies:
    1. Data generation works with metadata
    2. Chaos ops are applied and reported
    3. Metrics are exported
    4. All systems work together
    """
    endpoint = f"{base_url}/v1/schemas/{schema_name}/generate"
    
    # Phase 1: Generate data with metadata and chaos
    gen_resp = requests.get(
        endpoint,
        params={
            "count": 10,
            "chaos_ops": "schema_field_nulling",
            "include_metadata": "true"
        },
        timeout=timeout
    )
    gen_resp.raise_for_status()
    data = gen_resp.json()
    
    # Verify response structure
    assert "items" in data, "Expected items in response"
    assert "_metadata" in data, "Expected metadata in response"
    assert len(data["items"]) == 10, "Expected 10 items"
    
    # Verify metadata completeness
    metadata = data["_metadata"]
    assert "seed" in metadata
    assert "schema" in metadata
    assert "chaos_applied" in metadata
    
    # Phase 2: Verify metrics were recorded
    metrics_resp = requests.get(f"{base_url}/metrics", timeout=timeout)
    metrics_resp.raise_for_status()
    metrics_text = metrics_resp.text
    
    # Verify core metrics exist
    assert "items_generated_total" in metrics_text
    assert f'schema="{schema_name}"' in metrics_text or f"schema=\"{schema_name}\"" in metrics_text
    
    # Phase 3: Verify config system is functional
    config_resp = requests.get(
        f"{base_url}/v1/admin/config/debug",
        timeout=timeout
    )
    config_resp.raise_for_status()
    config_data = config_resp.json()
    
    assert "server" in config_data or "generation" in config_data, \
        "Expected server or generation config in debug output"
    
    # Phase 4: Generate more data via WebSocket (if implemented)
    # This would test the WebSocket pipeline, but we'll skip for now
    # since WebSocket tests are in test_streaming_smoke.py
    
    print("\n=== End-to-End Pipeline Test ===")
    print(f"✓ Generated {len(data['items'])} items with metadata")
    print(f"✓ Chaos ops applied: {len(metadata.get('chaos_applied', []))}")
    print(f"✓ Metrics endpoint responding")
    print(f"✓ Config system functional")
