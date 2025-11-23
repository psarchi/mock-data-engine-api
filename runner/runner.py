"""Comprehensive chaos operation validator and test runner.

Tests each chaos operation individually with specific validators,
plus drift layering behavior (consistency, exhaustion, reversion).
"""
from __future__ import annotations

import json
import sys
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

try:
    from mock_engine.chaos.registry import get_registry
except Exception:
    get_registry = None  # type: ignore

BASE_URL = "http://127.0.0.1:8000"
SCHEMA_NAME = "ga4"
COUNT = 3
SEED = 123
LOG_PATH = Path(__file__).parent / "log.log"


@dataclass
class TestResult:
    """Result of a single test."""
    op_name: str
    test_name: str
    passed: bool
    message: str
    details: List[str] = field(default_factory=list)


@dataclass
class TestSuite:
    """Collection of test results."""
    results: List[TestResult] = field(default_factory=list)

    def add(self, result: TestResult):
        self.results.append(result)

    def summary(self) -> str:
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed
        pct = (passed / total * 100) if total > 0 else 0
        return f"SUMMARY: {passed}/{total} passed ({pct:.1f}%), {failed} failed"

    def print_results(self, f):
        for r in self.results:
            status = "✓ PASS" if r.passed else "✗ FAIL"
            print(f"{status}: {r.op_name} - {r.test_name}", file=f)
            print(f"  {r.message}", file=f)
            for detail in r.details[:10]:
                print(f"    {detail}", file=f)
            if len(r.details) > 10:
                print(f"    ... {len(r.details) - 10} more details", file=f)
        print(f"\n{self.summary()}", file=f)


def fetch_generate(
    name: str,
    *,
    chaos_ops: str | None = None,
    seed: int | None = None,
    count: int | None = None,
) -> Tuple[Dict[str, Any], int, Dict[str, str], float]:
    """Fetch generation endpoint with optional chaos ops."""
    params = {"count": count or COUNT, "seed": seed if seed is not None else SEED}
    if chaos_ops is not None:
        params["chaos_ops"] = chaos_ops
    query = urllib.parse.urlencode(params)
    url = f"{BASE_URL}/v1/schemas/{name}/generate?{query}"
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(url) as resp:  # noqa: S310
            raw = resp.read()
            status = getattr(resp, "status", 0)
            headers = {k.lower(): v for k, v in resp.headers.items()}
    except urllib.error.HTTPError as e:
        # Chaos ops can return error status codes - treat as valid responses
        raw = e.read()
        status = e.code
        headers = {k.lower(): v for k, v in e.headers.items()}
    elapsed = time.monotonic() - t0
    return json.loads(raw.decode("utf-8")), status, headers, elapsed


def collect_ops() -> List[str]:
    """Get list of available chaos ops from registry."""
    if callable(get_registry):
        try:
            return sorted(get_registry().keys())
        except Exception:
            pass
    return [
        "latency",
        "http_error",
        "http_mismatch",
        "list_shuffle",
        "duplicate_items",
        "encoding_corrupt",
        "partial_load",
        "schema_bloat",
        "schema_time_skew",
        "schema_field_nulling",
        "truncate",
        "time_skew",
        "header_anomaly",
        "auth_fault",
        "random_header_case",
        "data_drift",
        "schema_drift",
    ]


def diff_payloads(a: dict, b: dict) -> List[str]:
    """Find differences between two payloads."""
    def _diff(x: Any, y: Any, path: str = "") -> List[str]:
        diffs: List[str] = []
        if type(x) != type(y):
            diffs.append(f"{path or '<root>'}: type {type(x).__name__} -> {type(y).__name__}")
            return diffs
        if isinstance(x, dict):
            keys = set(x) | set(y)
            for k in sorted(keys):
                p = f"{path}.{k}" if path else str(k)
                if k not in x:
                    diffs.append(f"{p}: <missing> -> present")
                elif k not in y:
                    diffs.append(f"{p}: present -> <missing>")
                else:
                    diffs.extend(_diff(x[k], y[k], p))
        elif isinstance(x, list):
            if len(x) != len(y):
                diffs.append(f"{path or '<list>'}: len {len(x)} -> {len(y)}")
            for idx, (vx, vy) in enumerate(zip(x, y)):
                diffs.extend(_diff(vx, vy, f"{path}[{idx}]"))
        elif x != y:
            xr = repr(x)[:100]
            yr = repr(y)[:100]
            diffs.append(f"{path or '<root>'}: {xr} -> {yr}")
        return diffs
    return _diff(a, b)


# =============================================================================
# OPERATION-SPECIFIC VALIDATORS
# =============================================================================

def validate_latency(baseline: dict, variant: dict, elapsed_ms: float) -> TestResult:
    """Validate latency operation added delay."""
    # Latency should not change payload, only add time
    diffs = diff_payloads(baseline, variant)
    if diffs:
        return TestResult(
            "latency", "no_payload_change", False,
            f"Latency should not change payload, found {len(diffs)} diffs",
            diffs[:5]
        )
    if elapsed_ms < 60:  # min_ms from config
        return TestResult(
            "latency", "min_delay", False,
            f"Expected latency >= 60ms, got {elapsed_ms:.2f}ms"
        )
    return TestResult(
        "latency", "adds_delay", True,
        f"Added {elapsed_ms:.2f}ms latency without changing payload"
    )


def validate_http_error(status: int, base_status: int) -> TestResult:
    """Validate http_error returns error status code."""
    expected_codes = [429, 500, 502]
    if status in expected_codes:
        return TestResult(
            "http_error", "error_status", True,
            f"Returned error status {status}"
        )
    return TestResult(
        "http_error", "error_status", False,
        f"Expected status in {expected_codes}, got {status}"
    )


def validate_http_mismatch(status: int, base_status: int, baseline: dict, variant: dict) -> TestResult:
    """Validate http_mismatch returns non-2xx status but same body."""
    if status == base_status:
        return TestResult(
            "http_mismatch", "status_changed", False,
            f"Expected status to change from {base_status}, got {status}"
        )
    # Body should be unchanged
    diffs = diff_payloads(baseline, variant)
    if diffs:
        return TestResult(
            "http_mismatch", "body_unchanged", False,
            f"Body should be unchanged, found {len(diffs)} diffs"
        )
    return TestResult(
        "http_mismatch", "mismatch_status_ok_body", True,
        f"Status {status} with unchanged body (mismatch achieved)"
    )


def validate_list_shuffle(baseline: dict, variant: dict) -> TestResult:
    """Validate list_shuffle reordered items."""
    base_items = baseline.get("items", [])
    var_items = variant.get("items", [])
    if len(base_items) != len(var_items):
        return TestResult(
            "list_shuffle", "same_count", False,
            f"Item count changed: {len(base_items)} -> {len(var_items)}"
        )
    # Check if order changed (items should be same set, different order)
    if base_items == var_items:
        return TestResult(
            "list_shuffle", "order_changed", False,
            "Items not shuffled (same order)"
        )
    return TestResult(
        "list_shuffle", "shuffled", True,
        f"Items shuffled (count={len(var_items)})"
    )


def validate_schema_drift(baseline: dict, variant: dict, chaos_desc: List[str]) -> TestResult:
    """Validate schema_drift modified schema structure."""
    if not chaos_desc or "schema_drift" not in str(chaos_desc):
        return TestResult(
            "schema_drift", "activated", False,
            "schema_drift did not activate or report changes"
        )
    diffs = diff_payloads(baseline, variant)
    # Should have structural changes (added/dropped/renamed fields)
    if not diffs:
        return TestResult(
            "schema_drift", "schema_changed", False,
            "No structural changes detected"
        )
    return TestResult(
        "schema_drift", "schema_mutated", True,
        f"{len(diffs)} structural changes: {chaos_desc}",
        diffs[:5]
    )


def validate_data_drift(baseline: dict, variant: dict, chaos_desc: List[str]) -> TestResult:
    """Validate data_drift modified field values."""
    if not chaos_desc or "data_drift" not in str(chaos_desc):
        return TestResult(
            "data_drift", "activated", False,
            "data_drift did not activate or report changes"
        )
    diffs = diff_payloads(baseline, variant)
    if not diffs:
        return TestResult(
            "data_drift", "values_changed", False,
            "No value changes detected"
        )
    return TestResult(
        "data_drift", "values_mutated", True,
        f"{len(diffs)} value changes: {chaos_desc}",
        diffs[:5]
    )


def validate_truncate(baseline: dict, variant: dict) -> TestResult:
    """Validate truncate operation shortened strings."""
    diffs = diff_payloads(baseline, variant)
    if not diffs:
        return TestResult(
            "truncate", "strings_truncated", False,
            "No changes detected (truncate may not have activated)"
        )
    # Check if changes involve shorter strings
    truncations = [d for d in diffs if "->" in d and "..." not in d]
    if truncations:
        return TestResult(
            "truncate", "strings_truncated", True,
            f"{len(truncations)} fields truncated",
            truncations[:5]
        )
    return TestResult(
        "truncate", "strings_truncated", True,
        f"{len(diffs)} changes detected (truncation applied)"
    )


def validate_duplicate_items(baseline: dict, variant: dict) -> TestResult:
    """Validate duplicate_items added duplicate records."""
    base_items = baseline.get("items", [])
    var_items = variant.get("items", [])
    if len(var_items) <= len(base_items):
        return TestResult(
            "duplicate_items", "items_duplicated", False,
            f"Expected more items, got {len(var_items)} vs baseline {len(base_items)}"
        )
    return TestResult(
        "duplicate_items", "items_duplicated", True,
        f"Items increased: {len(base_items)} -> {len(var_items)}"
    )


def validate_schema_field_nulling(baseline: dict, variant: dict) -> TestResult:
    """Validate schema_field_nulling set fields to null."""
    diffs = diff_payloads(baseline, variant)
    nulled = [d for d in diffs if "None" in d or "null" in d.lower()]
    if not nulled:
        return TestResult(
            "schema_field_nulling", "fields_nulled", False,
            "No null values detected"
        )
    return TestResult(
        "schema_field_nulling", "fields_nulled", True,
        f"{len(nulled)} fields nulled",
        nulled[:5]
    )


def validate_time_skew(baseline: dict, variant: dict) -> TestResult:
    """Validate time_skew modified timestamp fields."""
    diffs = diff_payloads(baseline, variant)
    if not diffs:
        return TestResult(
            "time_skew", "timestamps_skewed", False,
            "No changes detected"
        )
    # Look for timestamp-like changes
    time_changes = [d for d in diffs if any(x in d.lower() for x in ["time", "date", "timestamp"])]
    if time_changes:
        return TestResult(
            "time_skew", "timestamps_skewed", True,
            f"{len(time_changes)} timestamp fields modified",
            time_changes[:5]
        )
    return TestResult(
        "time_skew", "timestamps_skewed", True,
        f"{len(diffs)} changes detected (time skew applied)"
    )


def validate_auth_fault(status: int) -> TestResult:
    """Validate auth_fault returns auth error status."""
    expected_codes = [401, 403]
    if status in expected_codes:
        return TestResult(
            "auth_fault", "auth_error_status", True,
            f"Returned auth error status {status}"
        )
    return TestResult(
        "auth_fault", "auth_error_status", False,
        f"Expected status in {expected_codes}, got {status}"
    )


def validate_header_anomaly(base_headers: Dict[str, str], headers: Dict[str, str]) -> TestResult:
    """Validate header_anomaly modified response headers."""
    diffs = []
    for k in set(base_headers) | set(headers):
        if base_headers.get(k) != headers.get(k):
            diffs.append(f"{k}: {base_headers.get(k)} -> {headers.get(k)}")
    if not diffs:
        return TestResult(
            "header_anomaly", "headers_modified", False,
            "No header changes detected"
        )
    return TestResult(
        "header_anomaly", "headers_modified", True,
        f"{len(diffs)} headers modified",
        diffs[:5]
    )


def validate_random_header_case(base_headers: Dict[str, str], headers: Dict[str, str]) -> TestResult:
    """Validate random_header_case modified header value casing."""
    # Check if any header value has different casing
    diffs = []
    for k in set(base_headers.keys()) & set(headers.keys()):
        base_val = base_headers.get(k, "")
        chaos_val = headers.get(k, "")
        # Check if values differ in case but are the same when lowercased
        if base_val != chaos_val and base_val.lower() == chaos_val.lower():
            diffs.append(f"{k}: '{base_val}' -> '{chaos_val}'")

    if not diffs:
        return TestResult(
            "random_header_case", "header_case_changed", False,
            "No header case changes detected"
        )
    return TestResult(
        "random_header_case", "header_case_changed", True,
        f"{len(diffs)} header values changed case",
        diffs[:5]
    )


def validate_generic(op_name: str, baseline: dict, variant: dict) -> TestResult:
    """Generic validator - just check something changed."""
    diffs = diff_payloads(baseline, variant)
    if diffs:
        return TestResult(
            op_name, "payload_changed", True,
            f"{len(diffs)} changes detected",
            diffs[:3]
        )
    return TestResult(
        op_name, "payload_changed", False,
        "No changes detected (op may not have activated)"
    )


# =============================================================================
# DRIFT LAYER TESTS
# =============================================================================

def clear_drift_layers():
    """Clear all drift layers to start fresh."""
    try:
        import urllib.request
        url = f"{BASE_URL}/v1/admin/chaos/clear-drift"
        req = urllib.request.Request(url, method="POST")  # noqa: S310
        with urllib.request.urlopen(req) as resp:  # noqa: S310
            pass
    except Exception:
        # If endpoint doesn't exist, layers will naturally exhaust
        pass


def test_schema_drift_consistency(suite: TestSuite):
    """Test that schema_drift layer stays consistent for max_hits requests."""
    print(f"\n{'='*60}")
    print("TEST: Schema Drift Layer Consistency")
    print(f"{'='*60}")
    clear_drift_layers()

    # Activate schema_drift to create layer 0
    print("Step 1: Activate schema_drift (create layer 0)")
    variant1, _, _, _ = fetch_generate(SCHEMA_NAME, chaos_ops="schema_drift", seed=999)
    variant1.pop("chaos_descriptions", None)

    # Make 9 more requests (total 10) - should all use same schema
    mutations_seen = set()
    for i in range(2, 11):
        print(f"Step {i}: Normal generation (should use layer 0)")
        variantN, _, _, _ = fetch_generate(SCHEMA_NAME, seed=999)
        variantN.pop("chaos_descriptions", None)

        # Compare with variant1 - should be identical
        diffs = diff_payloads(variant1, variantN)
        if diffs:
            suite.add(TestResult(
                "schema_drift", "consistency_test", False,
                f"Request {i}/10 differs from request 1 (layer should be consistent)",
                diffs[:5]
            ))
            return
        mutations_seen.add(json.dumps(variantN.get("items", [])[:1], sort_keys=True))

    if len(mutations_seen) > 1:
        suite.add(TestResult(
            "schema_drift", "consistency_test", False,
            f"Detected {len(mutations_seen)} different schemas (should be 1)"
        ))
    else:
        suite.add(TestResult(
            "schema_drift", "consistency_test", True,
            "All 10 requests used same schema (layer 0 consistent)"
        ))


def test_schema_drift_layering(suite: TestSuite):
    """Test schema_drift layering: layer 0 -> layer 1 -> exhaust -> revert."""
    print(f"\n{'='*60}")
    print("TEST: Schema Drift Layering")
    print(f"{'='*60}")
    clear_drift_layers()

    # Step 1: Create layer 0
    print("Step 1: Create layer 0")
    layer0_resp, _, _, _ = fetch_generate(SCHEMA_NAME, chaos_ops="schema_drift", seed=888)
    layer0_resp.pop("chaos_descriptions", None)

    # Step 2-3: Normal requests (should use layer 0)
    print("Step 2-3: Normal requests (use layer 0)")
    for i in range(2):
        resp, _, _, _ = fetch_generate(SCHEMA_NAME, seed=888)
        resp.pop("chaos_descriptions", None)
        diffs = diff_payloads(layer0_resp, resp)
        if diffs:
            suite.add(TestResult(
                "schema_drift", "layering_layer0_consistent", False,
                f"Request {i+2} differs from layer 0"
            ))
            return

    # Step 4: Create layer 1 (compounding mutations)
    print("Step 4: Create layer 1 (should compound on layer 0)")
    layer1_resp, _, _, _ = fetch_generate(SCHEMA_NAME, chaos_ops="schema_drift", seed=888)
    layer1_resp.pop("chaos_descriptions", None)

    # Layer 1 should be DIFFERENT from layer 0 (has additional mutations)
    diffs_0_to_1 = diff_payloads(layer0_resp, layer1_resp)
    if not diffs_0_to_1:
        suite.add(TestResult(
            "schema_drift", "layering_layer1_created", False,
            "Layer 1 identical to layer 0 (should have new mutations)"
        ))
        return

    # Step 5-14: Normal requests (should use layer 1 for 10 requests total)
    print("Step 5-14: Normal requests (use layer 1 for 10 total hits)")
    for i in range(5, 15):
        resp, _, _, _ = fetch_generate(SCHEMA_NAME, seed=888)
        resp.pop("chaos_descriptions", None)
        diffs = diff_payloads(layer1_resp, resp)
        if diffs:
            suite.add(TestResult(
                "schema_drift", "layering_layer1_consistent", False,
                f"Request {i} differs from layer 1"
            ))
            return

    # Step 15: Layer 1 should be exhausted, revert to layer 0
    print("Step 15: Layer 1 exhausted, should revert to layer 0")
    revert_resp, _, _, _ = fetch_generate(SCHEMA_NAME, seed=888)
    revert_resp.pop("chaos_descriptions", None)

    # Should match layer 0 now
    diffs_revert = diff_payloads(layer0_resp, revert_resp)
    if diffs_revert:
        suite.add(TestResult(
            "schema_drift", "layering_revert_to_layer0", False,
            f"After layer 1 exhausted, should revert to layer 0, found {len(diffs_revert)} diffs"
        ))
    else:
        suite.add(TestResult(
            "schema_drift", "layering_full_cycle", True,
            "Layer 0 -> Layer 1 -> Exhaust -> Revert to Layer 0 successful"
        ))


def test_drift_exhaustion(suite: TestSuite):
    """Test that drift layer exhausts and reverts to base schema."""
    print(f"\n{'='*60}")
    print("TEST: Drift Layer Exhaustion")
    print(f"{'='*60}")
    clear_drift_layers()

    # Get baseline (no drift)
    print("Step 1: Get baseline (no drift)")
    baseline, _, _, _ = fetch_generate(SCHEMA_NAME, seed=777)
    baseline.pop("chaos_descriptions", None)

    # Create drift layer
    print("Step 2: Create drift layer")
    fetch_generate(SCHEMA_NAME, chaos_ops="schema_drift", seed=777)

    # Use for 10 requests (exhaust)
    print("Step 3-12: Use drift layer 10 times (exhaust)")
    for i in range(10):
        fetch_generate(SCHEMA_NAME, seed=777)

    # Request 13 should revert to baseline
    print("Step 13: After exhaustion, should revert to baseline")
    after_exhaust, _, _, _ = fetch_generate(SCHEMA_NAME, seed=777)
    after_exhaust.pop("chaos_descriptions", None)

    diffs = diff_payloads(baseline, after_exhaust)
    if diffs:
        suite.add(TestResult(
            "schema_drift", "exhaustion_reverts", False,
            f"After exhaustion, schema differs from baseline: {len(diffs)} diffs",
            diffs[:5]
        ))
    else:
        suite.add(TestResult(
            "schema_drift", "exhaustion_reverts", True,
            "After 10 hits, layer exhausted and reverted to base schema"
        ))


# =============================================================================
# MAIN TEST RUNNER
# =============================================================================

def main() -> int:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        fh = LOG_PATH.open("w", encoding="utf-8")
    except Exception:
        fh = sys.stdout

    suite = TestSuite()

    with fh as f:
        print(f"# Chaos Test Runner - {datetime.utcnow().isoformat()}Z", file=f)
        print(f"# URL: {BASE_URL}, Schema: {SCHEMA_NAME}, Count: {COUNT}, Seed: {SEED}", file=f)
        print(f"{'='*60}", file=f)

        # Get baseline
        print("\n## Fetching baseline (no chaos)", file=f)
        baseline, base_status, base_headers, base_time = fetch_generate(SCHEMA_NAME)
        baseline.pop("chaos_descriptions", None)
        print(f"Baseline: status={base_status}, time={base_time*1000:.2f}ms", file=f)

        # Test each operation
        ops = collect_ops()
        print(f"\n## Testing {len(ops)} operations\n", file=f)

        validators = {
            "latency": lambda baseline, variant, status, headers, elapsed, desc:  # type: ignore
                validate_latency(baseline, variant, elapsed * 1000),
            "http_error": lambda baseline, variant, status, headers, elapsed, desc:  # type: ignore
                validate_http_error(status, base_status),
            "http_mismatch": lambda baseline, variant, status, headers, elapsed, desc:  # type: ignore
                validate_http_mismatch(status, base_status, baseline, variant),
            "list_shuffle": lambda baseline, variant, status, headers, elapsed, desc:  # type: ignore
                validate_list_shuffle(baseline, variant),
            "schema_drift": lambda baseline, variant, status, headers, elapsed, desc:  # type: ignore
                validate_schema_drift(baseline, variant, desc),
            "data_drift": lambda baseline, variant, status, headers, elapsed, desc:  # type: ignore
                validate_data_drift(baseline, variant, desc),
            "truncate": lambda baseline, variant, status, headers, elapsed, desc:  # type: ignore
                validate_truncate(baseline, variant),
            "duplicate_items": lambda baseline, variant, status, headers, elapsed, desc:  # type: ignore
                validate_duplicate_items(baseline, variant),
            "schema_field_nulling": lambda baseline, variant, status, headers, elapsed, desc:  # type: ignore
                validate_schema_field_nulling(baseline, variant),
            "time_skew": lambda baseline, variant, status, headers, elapsed, desc:  # type: ignore
                validate_time_skew(baseline, variant),
            "auth_fault": lambda baseline, variant, status, headers, elapsed, desc:  # type: ignore
                validate_auth_fault(status),
            "header_anomaly": lambda baseline, variant, status, headers, elapsed, desc:  # type: ignore
                validate_header_anomaly(base_headers, headers),
            "random_header_case": lambda baseline, variant, status, headers, elapsed, desc:  # type: ignore
                validate_random_header_case(base_headers, headers),
        }

        for op in ops:
            print(f"Testing: {op}", file=f)
            try:
                variant, status, headers, elapsed = fetch_generate(SCHEMA_NAME, chaos_ops=op)
                chaos_desc = variant.pop("chaos_descriptions", [])

                # Run validator
                validator = validators.get(op, lambda b, v, s, h, t, d: validate_generic(op, b, v))
                result = validator(baseline, variant, status, headers, elapsed, chaos_desc)
                suite.add(result)

            except Exception as exc:
                suite.add(TestResult(
                    op, "execution", False,
                    f"Exception during test: {exc}"
                ))

            time.sleep(0.05)

        # Drift-specific tests
        print(f"\n{'='*60}", file=f)
        print("## DRIFT LAYER TESTS", file=f)
        print(f"{'='*60}\n", file=f)

        test_schema_drift_consistency(suite)
        test_schema_drift_layering(suite)
        test_drift_exhaustion(suite)

        # Print results
        print(f"\n{'='*60}", file=f)
        print("## TEST RESULTS", file=f)
        print(f"{'='*60}\n", file=f)
        suite.print_results(f)

    print(f"\nLog written to {LOG_PATH}")
    return 0 if all(r.passed for r in suite.results) else 1


if __name__ == "__main__":
    sys.exit(main())
