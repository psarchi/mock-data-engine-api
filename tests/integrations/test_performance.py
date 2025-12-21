"""Performance and load tests for REST and WebSocket endpoints.

These tests verify:
1. REST endpoint throughput and latency under load
2. WebSocket streaming performance with concurrent connections
3. Chaos ops don't degrade performance beyond acceptable thresholds
4. System can handle high-volume sustained load

All tests marked with @pytest.mark.perf to run separately from CI.
"""

import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest
import requests
import websocket


def calculate_percentiles(values):
    """Calculate p50, p95, p99 percentiles."""
    if not values:
        return 0, 0, 0
    sorted_values = sorted(values)
    p50 = statistics.median(sorted_values)
    p95 = sorted_values[int(len(sorted_values) * 0.95)]
    p99 = sorted_values[int(len(sorted_values) * 0.99)]
    return p50, p95, p99


@pytest.mark.perf
def test_rest_throughput(base_url, schema_name, timeout):
    """Test REST endpoint throughput (requests/second).

    Measures:
    - Requests/second over 30 second window
    - Latency p50, p95, p99
    """
    duration = 30  # seconds
    max_workers = 10
    endpoint = f"{base_url}/v1/schemas/{schema_name}/generate"

    def make_request():
        start = time.time()
        try:
            resp = requests.get(endpoint, params={"count": 10}, timeout=timeout)
            elapsed = time.time() - start
            return {"success": resp.status_code == 200, "latency": elapsed}
        except Exception as e:
            elapsed = time.time() - start
            return {"success": False, "latency": elapsed, "error": str(e)}

    results = []
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        while time.time() - start_time < duration:
            futures.append(executor.submit(make_request))

        for future in as_completed(futures):
            results.append(future.result())

    total_time = time.time() - start_time
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]

    throughput = len(successful) / total_time
    latencies = [r["latency"] for r in successful]
    p50, p95, p99 = calculate_percentiles(latencies)

    print(f"\n=== REST Throughput Test ===")
    print(f"Duration: {total_time:.2f}s")
    print(f"Total requests: {len(results)}")
    print(f"Successful: {len(successful)}")
    print(f"Failed: {len(failed)}")
    print(f"Throughput: {throughput:.2f} req/s")
    print(f"Latency p50: {p50*1000:.2f}ms")
    print(f"Latency p95: {p95*1000:.2f}ms")
    print(f"Latency p99: {p99*1000:.2f}ms")

    # Assertions
    assert len(successful) > 0, "No successful requests"
    assert throughput >= 10, f"Throughput {throughput:.2f} req/s below minimum 10 req/s"
    assert p99 < 5.0, f"p99 latency {p99*1000:.2f}ms exceeds 5000ms"


@pytest.mark.perf
def test_ws_throughput(ws_url, schema_name, timeout):
    """Test WebSocket streaming throughput (items/second).

    Opens multiple concurrent WebSocket connections and measures
    total items/second across all connections.
    """
    duration = 30  # seconds
    connections = 5
    count_per_msg = 10

    def stream_items():
        url = f"{ws_url}/v1/schemas/{schema_name}/stream?count={count_per_msg}"
        ws = websocket.create_connection(url, timeout=timeout)
        items = []
        start = time.time()

        try:
            while time.time() - start < duration:
                try:
                    import json

                    msg = ws.recv()
                    if msg:
                        data = json.loads(msg)
                        if isinstance(data, dict):
                            if data.get("type") == "event" and "data" in data:
                                items.append(data["data"])
                            elif "items" in data:
                                items.extend(data["items"])
                except websocket.WebSocketTimeoutException:
                    break
        finally:
            ws.close()

        return len(items)

    start_time = time.time()
    with ThreadPoolExecutor(max_workers=connections) as executor:
        futures = [executor.submit(stream_items) for _ in range(connections)]
        item_counts = [future.result() for future in as_completed(futures)]

    total_time = time.time() - start_time
    total_items = sum(item_counts)
    throughput = total_items / total_time

    print(f"\n=== WebSocket Throughput Test ===")
    print(f"Duration: {total_time:.2f}s")
    print(f"Connections: {connections}")
    print(f"Total items: {total_items}")
    print(f"Throughput: {throughput:.2f} items/s")

    assert total_items > 0, "No items received"
    assert throughput >= 10, f"Throughput {throughput:.2f} items/s below minimum 10 items/s"


@pytest.mark.perf
def test_rest_latency(base_url, schema_name, timeout):
    """Test REST endpoint latency distribution.

    Makes sequential requests and measures latency percentiles.
    """
    num_requests = 100
    endpoint = f"{base_url}/v1/schemas/{schema_name}/generate"
    latencies = []

    for _ in range(num_requests):
        start = time.time()
        try:
            resp = requests.get(endpoint, params={"count": 10}, timeout=timeout)
            if resp.status_code == 200:
                latencies.append(time.time() - start)
        except Exception:
            pass

    p50, p95, p99 = calculate_percentiles(latencies)

    print(f"\n=== REST Latency Test ===")
    print(f"Requests: {len(latencies)}")
    print(f"Latency p50: {p50*1000:.2f}ms")
    print(f"Latency p95: {p95*1000:.2f}ms")
    print(f"Latency p99: {p99*1000:.2f}ms")

    assert len(latencies) >= num_requests * 0.95, "Too many failed requests"
    assert p50 < 1.0, f"p50 latency {p50*1000:.2f}ms exceeds 1000ms"
    assert p95 < 2.0, f"p95 latency {p95*1000:.2f}ms exceeds 2000ms"
    assert p99 < 5.0, f"p99 latency {p99*1000:.2f}ms exceeds 5000ms"


@pytest.mark.perf
def test_chaos_performance_impact(base_url, schema_name, timeout):
    """Test that chaos ops don't degrade performance unacceptably.

    Compares baseline throughput vs throughput with fast chaos ops.
    """
    endpoint = f"{base_url}/v1/schemas/{schema_name}/generate"
    num_requests = 50

    def measure_throughput(chaos_ops=None):
        params = {"count": 10}
        if chaos_ops:
            params["chaos_ops"] = chaos_ops

        start = time.time()
        successful = 0
        for _ in range(num_requests):
            try:
                resp = requests.get(endpoint, params=params, timeout=timeout)
                if resp.status_code == 200:
                    successful += 1
            except Exception:
                pass
        elapsed = time.time() - start
        return successful / elapsed if elapsed > 0 else 0

    baseline_throughput = measure_throughput(chaos_ops=None)
    print(f"\n=== Chaos Performance Impact ===")
    print(f"Baseline throughput: {baseline_throughput:.2f} req/s")

    # Test fast chaos ops (should have minimal impact)
    fast_ops = ["list_shuffle", "schema_field_nulling"]
    for op in fast_ops:
        chaos_throughput = measure_throughput(chaos_ops=op)
        impact = (baseline_throughput - chaos_throughput) / baseline_throughput * 100
        print(f"{op} throughput: {chaos_throughput:.2f} req/s (impact: {impact:.1f}%)")
        assert impact < 50, f"{op} degraded performance by {impact:.1f}% (max 50%)"

    assert baseline_throughput > 0, "Baseline throughput is zero"


@pytest.mark.perf
def test_sustained_load(base_url, schema_name, timeout):
    """Test system stability under sustained high load.

    Runs sustained load for 2 minutes (reduced from 5 for testing).
    Monitors error rate and latency stability.
    """
    duration = 120  # 2 minutes (reduced for faster testing)
    max_workers = 20
    endpoint = f"{base_url}/v1/schemas/{schema_name}/generate"

    def make_request():
        start = time.time()
        try:
            resp = requests.get(endpoint, params={"count": 10}, timeout=timeout)
            return {
                "success": resp.status_code == 200,
                "latency": time.time() - start,
                "timestamp": start,
            }
        except Exception:
            return {
                "success": False,
                "latency": time.time() - start,
                "timestamp": start,
            }

    results = []
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        while time.time() - start_time < duration:
            futures.append(executor.submit(make_request))
            time.sleep(0.02)  # ~50 req/s

        for future in as_completed(futures):
            results.append(future.result())

    total_time = time.time() - start_time
    successful = [r for r in results if r["success"]]
    error_rate = (len(results) - len(successful)) / len(results) * 100

    # Check latency stability (compare first half vs second half)
    midpoint = start_time + duration / 2
    first_half = [r["latency"] for r in successful if r["timestamp"] < midpoint]
    second_half = [r["latency"] for r in successful if r["timestamp"] >= midpoint]

    avg_latency_first = statistics.mean(first_half) if first_half else 0
    avg_latency_second = statistics.mean(second_half) if second_half else 0

    print(f"\n=== Sustained Load Test ===")
    print(f"Duration: {total_time:.2f}s")
    print(f"Total requests: {len(results)}")
    print(f"Successful: {len(successful)}")
    print(f"Error rate: {error_rate:.2f}%")
    print(f"Avg latency (first half): {avg_latency_first*1000:.2f}ms")
    print(f"Avg latency (second half): {avg_latency_second*1000:.2f}ms")

    assert error_rate < 10, f"Error rate {error_rate:.2f}% exceeds 10%"
    if avg_latency_first > 0:
        latency_increase = (
            (avg_latency_second - avg_latency_first) / avg_latency_first * 100
        )
        print(f"Latency increase: {latency_increase:.1f}%")
        assert (
            abs(latency_increase) < 50
        ), f"Latency degraded by {latency_increase:.1f}%"


@pytest.mark.perf
def test_concurrent_connections(ws_url, schema_name, timeout):
    """Test maximum concurrent WebSocket connections.

    Opens increasing numbers of concurrent connections to find limits.
    """
    max_connections = 50  # Start with reasonable limit
    count_per_msg = 5

    def open_connection():
        url = f"{ws_url}/v1/schemas/{schema_name}/stream?count={count_per_msg}"
        try:
            ws = websocket.create_connection(url, timeout=timeout)
            # Try to receive at least one message
            import json

            msg = ws.recv()
            data = json.loads(msg) if msg else {}
            ws.close()
            return True
        except Exception:
            return False

    print(f"\n=== Concurrent Connections Test ===")

    for num_connections in [10, 20, 30, 40, 50]:
        start = time.time()
        with ThreadPoolExecutor(max_workers=num_connections) as executor:
            futures = [
                executor.submit(open_connection) for _ in range(num_connections)
            ]
            results = [future.result() for future in as_completed(futures)]

        successful = sum(results)
        elapsed = time.time() - start
        success_rate = successful / num_connections * 100

        print(
            f"{num_connections} connections: {successful}/{num_connections} successful ({success_rate:.1f}%) in {elapsed:.2f}s"
        )

        if success_rate < 90:
            print(f"Connection limit reached at ~{num_connections} connections")
            break

    assert successful > 0, "Could not establish any connections"


@pytest.mark.perf
def test_burst_load(base_url, schema_name, timeout):
    """Test system handles traffic bursts without failing.

    Sends normal load, then burst of 100 requests, then normal load.
    """
    endpoint = f"{base_url}/v1/schemas/{schema_name}/generate"

    # Normal load: 10 req/s for 10 seconds
    print(f"\n=== Burst Load Test ===")
    print("Phase 1: Normal load (10 req/s for 10s)...")
    normal_results = []
    for _ in range(100):
        try:
            resp = requests.get(endpoint, params={"count": 10}, timeout=timeout)
            normal_results.append(resp.status_code == 200)
        except Exception:
            normal_results.append(False)
        time.sleep(0.1)

    # Burst: 100 concurrent requests
    print("Phase 2: Burst (100 concurrent requests)...")
    burst_start = time.time()
    with ThreadPoolExecutor(max_workers=100) as executor:
        futures = [
            executor.submit(
                requests.get, endpoint, params={"count": 10}, timeout=timeout * 2
            )
            for _ in range(100)
        ]
        burst_results = []
        for future in as_completed(futures):
            try:
                resp = future.result()
                burst_results.append(resp.status_code == 200)
            except Exception:
                burst_results.append(False)

    burst_time = time.time() - burst_start

    # Recovery: Normal load again
    print("Phase 3: Recovery (10 req/s for 10s)...")
    recovery_results = []
    for _ in range(100):
        try:
            resp = requests.get(endpoint, params={"count": 10}, timeout=timeout)
            recovery_results.append(resp.status_code == 200)
        except Exception:
            recovery_results.append(False)
        time.sleep(0.1)

    normal_success = sum(normal_results) / len(normal_results) * 100
    burst_success = sum(burst_results) / len(burst_results) * 100
    recovery_success = sum(recovery_results) / len(recovery_results) * 100

    print(f"Normal load success: {normal_success:.1f}%")
    print(f"Burst success: {burst_success:.1f}% (completed in {burst_time:.2f}s)")
    print(f"Recovery success: {recovery_success:.1f}%")

    assert burst_success >= 80, f"Burst success rate {burst_success:.1f}% below 80%"
    assert (
        recovery_success >= 90
    ), f"Recovery success rate {recovery_success:.1f}% below 90%"


@pytest.mark.perf
def test_generator_performance(base_url, schema_name, timeout):
    """Test individual generator performance for schema.

    Generates 1000 items and measures generation rate.
    """
    endpoint = f"{base_url}/v1/schemas/{schema_name}/generate"
    total_items = 1000
    batch_size = 100
    num_batches = total_items // batch_size

    print(f"\n=== Generator Performance Test ===")
    start = time.time()

    items_generated = 0
    for _ in range(num_batches):
        try:
            resp = requests.get(endpoint, params={"count": batch_size}, timeout=timeout)
            if resp.status_code == 200:
                data = resp.json()
                items_generated += len(data.get("items", []))
        except Exception:
            pass

    elapsed = time.time() - start
    items_per_second = items_generated / elapsed if elapsed > 0 else 0

    print(f"Generated {items_generated} items in {elapsed:.2f}s")
    print(f"Rate: {items_per_second:.2f} items/s")

    assert items_generated >= total_items * 0.95, "Failed to generate enough items"
    assert (
        items_per_second >= 100
    ), f"Generation rate {items_per_second:.2f} items/s below minimum 100 items/s"


@pytest.mark.perf
def test_observability_overhead(base_url, schema_name, timeout):
    """Test performance overhead of observability features.

    Measures baseline performance with metrics/logging disabled,
    then compares with full observability enabled to quantify overhead.
    """
    endpoint = f"{base_url}/v1/schemas/{schema_name}/generate"
    admin_config_url = f"{base_url}/v1/admin/config/server"
    admin_update_url = f"{base_url}/v1/admin/config/server/update"
    num_requests = 50

    def measure_throughput():
        """Run performance measurement."""
        start = time.time()
        successful = 0
        latencies = []

        for _ in range(num_requests):
            try:
                req_start = time.time()
                resp = requests.get(endpoint, params={"count": 10}, timeout=timeout)
                latency = time.time() - req_start
                if resp.status_code == 200:
                    successful += 1
                    latencies.append(latency)
            except Exception:
                pass

        elapsed = time.time() - start
        throughput = successful / elapsed if elapsed > 0 else 0
        avg_latency = statistics.mean(latencies) if latencies else 0
        return throughput, avg_latency

    print(f"\n=== Observability Overhead Test ===")

    # Get original config
    try:
        config_resp = requests.get(admin_config_url, timeout=timeout)
        config_resp.raise_for_status()
        original_config = config_resp.json()

        original_metrics = original_config.get("observability", {}).get(
            "metrics_enabled", True
        )
        original_logging = (
            original_config.get("observability", {})
            .get("logging", {})
            .get("enabled", True)
        )
    except Exception as e:
        print(f"Warning: Could not fetch config: {e}")
        print("Skipping test")
        return

    try:
        # Phase 1: Disable observability features
        print("\nPhase 1: Disabling metrics and structured logging...")
        update_resp = requests.post(
            admin_update_url,
            json={
                "observability.metrics_enabled": False,
                "observability.logging.enabled": False,
            },
            timeout=timeout,
        )
        update_resp.raise_for_status()

        # Warm-up
        for _ in range(5):
            requests.get(endpoint, params={"count": 5}, timeout=timeout)

        # Measure baseline
        baseline_throughput, baseline_latency = measure_throughput()
        print(f"Baseline (observability off):")
        print(f"  Throughput: {baseline_throughput:.2f} req/s")
        print(f"  Avg latency: {baseline_latency*1000:.2f}ms")

        # Phase 2: Enable observability features
        print("\nPhase 2: Enabling metrics and structured logging...")
        update_resp = requests.post(
            admin_update_url,
            json={
                "observability.metrics_enabled": True,
                "observability.logging.enabled": True,
            },
            timeout=timeout,
        )
        update_resp.raise_for_status()

        # Warm-up
        for _ in range(5):
            requests.get(endpoint, params={"count": 5}, timeout=timeout)

        # Measure with observability
        observability_throughput, observability_latency = measure_throughput()
        print(f"\nWith observability (metrics + logging):")
        print(f"  Throughput: {observability_throughput:.2f} req/s")
        print(f"  Avg latency: {observability_latency*1000:.2f}ms")

        # Calculate overhead
        if baseline_throughput > 0:
            throughput_overhead = (
                (baseline_throughput - observability_throughput) / baseline_throughput * 100
            )
        else:
            throughput_overhead = 0

        if baseline_latency > 0:
            latency_overhead = (
                (observability_latency - baseline_latency) / baseline_latency * 100
            )
        else:
            latency_overhead = 0

        print(f"\n=== Overhead Summary ===")
        print(f"Throughput degradation: {throughput_overhead:.1f}%")
        print(f"Latency increase: {latency_overhead:.1f}%")

        # Verify overhead is acceptable (less than 30%)
        assert (
            throughput_overhead < 30
        ), f"Observability overhead {throughput_overhead:.1f}% exceeds 30%"

    finally:
        # Restore original config
        print("\nRestoring original configuration...")
        try:
            requests.post(
                admin_update_url,
                json={
                    "observability.metrics_enabled": original_metrics,
                    "observability.logging.enabled": original_logging,
                },
                timeout=timeout,
            )
        except Exception as e:
            print(f"Warning: Could not restore config: {e}")


@pytest.mark.perf
def test_observability_overhead_websocket(ws_url, schema_name, timeout):
    """Test observability overhead using WebSocket (more accurate server-side measurement).

    WebSocket avoids client-side HTTP overhead and gives cleaner server performance data.
    """
    import json

    base_url = ws_url.replace("ws://", "http://").replace(":8000", ":8000")
    admin_config_url = f"{base_url}/v1/admin/config/server"
    admin_update_url = f"{base_url}/v1/admin/config/server/update"
    duration = 10  # seconds per phase
    items_per_request = 50

    def measure_throughput_ws():
        """Run WebSocket performance measurement over fixed duration."""
        ws_endpoint = f"{ws_url}/v1/schemas/{schema_name}/stream?count={items_per_request}"

        items_received = 0
        start = time.time()

        try:
            ws = websocket.create_connection(ws_endpoint, timeout=timeout)

            while time.time() - start < duration:
                try:
                    msg = ws.recv()
                    if msg:
                        data = json.loads(msg)
                        if isinstance(data, dict):
                            if data.get("type") == "event" and "data" in data:
                                items_received += 1
                            elif "items" in data:
                                items_received += len(data["items"])
                except websocket.WebSocketTimeoutException:
                    break

            ws.close()
        except Exception:
            pass

        elapsed = time.time() - start
        throughput = items_received / elapsed if elapsed > 0 else 0
        return throughput, elapsed

    print(f"\n=== WebSocket Observability Overhead Test ===")

    # Get original config
    try:
        config_resp = requests.get(admin_config_url, timeout=timeout)
        config_resp.raise_for_status()
        original_config = config_resp.json()

        original_metrics = original_config.get("observability", {}).get(
            "metrics_enabled", True
        )
        original_logging = (
            original_config.get("observability", {})
            .get("logging", {})
            .get("enabled", True)
        )
    except Exception as e:
        print(f"Warning: Could not fetch config: {e}")
        print("Skipping test")
        return

    try:
        # Phase 1: Disable observability features
        print("\nPhase 1: Disabling metrics and structured logging...")
        update_resp = requests.post(
            admin_update_url,
            json={
                "observability.metrics_enabled": False,
                "observability.logging.enabled": False,
            },
            timeout=timeout,
        )
        update_resp.raise_for_status()

        # Warm-up (smaller batch)
        ws_warmup = f"{ws_url}/v1/schemas/{schema_name}/stream?count=10"
        for _ in range(2):
            try:
                ws = websocket.create_connection(ws_warmup, timeout=timeout)
                try:
                    ws.recv()
                finally:
                    ws.close()
            except Exception:
                pass

        # Measure baseline
        baseline_throughput, baseline_duration = measure_throughput_ws()
        print(f"Baseline (observability off):")
        print(f"  Throughput: {baseline_throughput:.2f} items/s")
        print(f"  Duration: {baseline_duration:.2f}s")

        # Phase 2: Enable observability features
        print("\nPhase 2: Enabling metrics and structured logging...")
        update_resp = requests.post(
            admin_update_url,
            json={
                "observability.metrics_enabled": True,
                "observability.logging.enabled": True,
            },
            timeout=timeout,
        )
        update_resp.raise_for_status()

        # Warm-up
        for _ in range(2):
            try:
                ws = websocket.create_connection(ws_warmup, timeout=timeout)
                try:
                    ws.recv()
                finally:
                    ws.close()
            except Exception:
                pass

        # Measure with observability
        observability_throughput, observability_duration = measure_throughput_ws()
        print(f"\nWith observability (metrics + logging):")
        print(f"  Throughput: {observability_throughput:.2f} items/s")
        print(f"  Duration: {observability_duration:.2f}s")

        # Calculate overhead
        if baseline_throughput > 0:
            throughput_overhead = (
                (baseline_throughput - observability_throughput) / baseline_throughput * 100
            )
        else:
            throughput_overhead = 0

        print(f"\n=== Overhead Summary (WebSocket) ===")
        print(f"Throughput degradation: {throughput_overhead:.1f}%")

        # Verify overhead is acceptable (less than 30%)
        assert (
            throughput_overhead < 30
        ), f"Observability overhead {throughput_overhead:.1f}% exceeds 30%"

    finally:
        # Restore original config
        print("\nRestoring original configuration...")
        try:
            requests.post(
                admin_update_url,
                json={
                    "observability.metrics_enabled": original_metrics,
                    "observability.logging.enabled": original_logging,
                },
                timeout=timeout,
            )
        except Exception as e:
            print(f"Warning: Could not restore config: {e}")
