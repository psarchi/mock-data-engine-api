# Chaos Engineering

Real pipelines deal with bad data. Missing fields, late-arriving events, corrupt payloads, upstream HTTP errors, gradual distribution drift - this stuff happens and your consumers need to handle it.

The engine has a built-in chaos layer with 19 operations that simulate exactly these failure modes. You can fire them on demand per request, or configure them to activate probabilistically so your tests encounter them naturally. Each op models a specific thing that goes wrong in production - not just random noise.

---

## How to enable it

### Per-request

```bash
# force specific ops by name (comma-separated)
curl "http://localhost:8000/v1/schemas/smoke/generate?chaos_ops=latency,schema_field_nulling"

curl "http://localhost:8000/v1/schemas/smoke/generate?chaos_ops=truncate,duplicate_items"
```

### Via config

Set `chaos.enabled: true` in `config/chaos.yaml` (or override in `config/` - see [Configuration](configuration.md)). Each op has its own `enabled` flag and activation probability `p`.

---

## Budget system

Two global caps prevent chaos from going completely off the rails:

| Setting | Default | What it does |
|---------|---------|-------------|
| `budgets.max_added_latency_ms` | 1500 | Total injected latency across all ops in one request |
| `budgets.max_faults_per_request` | 999 | Max request-phase fault ops (errors, auth failures, etc.) per request |

---

## Operations

Every op has:
- `enabled` - on/off toggle
- `p` - independent activation probability (0.0–1.0)
- `weight` - relative selection weight when the stochastic selector picks which ops run

### Network / server ops

#### latency
Sleeps for a random delay before returning the response. Simple but effective for testing timeout handling.

```yaml
latency:
  enabled: true
  p: 0.1        # 10% of requests
  min_ms: 60
  max_ms: 300
```

#### rate_drift
Variable latency following a wave pattern - sine, sawtooth, or random walk. Better than flat latency for simulating realistic throughput fluctuation.

```yaml
rate_drift:
  enabled: true
  p: 0.01
  pattern: sine       # sine | sawtooth | random_walk
  amp_ms: 250         # peak added latency
  period_s: 60.0      # wave period in seconds
  burst_prob: 0.05    # chance of a max-latency spike
  step_ms: 25         # max step per request (random walk only)
```

#### http_error
Short-circuits the request and returns an error status code - no body. Tests whether your consumer retries properly.

```yaml
http_error:
  enabled: true
  p: 0.01
  codes: [429, 500, 502]
```

#### http_mismatch
Returns a non-2xx status code but leaves the response body intact - so the body and status contradict each other. Nasty edge case that trips up clients that check status codes.

```yaml
http_mismatch:
  enabled: true
  p: 0.01
  codes: [400, 401, 403, 409, 412, 422, 429, 500, 502, 503]
```

#### auth_fault
Simulates auth failures. Three modes:
- `reject` - returns 401 or 403
- `drop` - strips the Authorization header
- `invalid` - marks the token as invalid in response meta

```yaml
auth_fault:
  enabled: true
  p: 0.01
  modes: [reject, drop, invalid]
  codes: [401, 403]
```

#### burst
Temporarily cranks the rate limiter to max throughput - simulates a traffic spike. Only relevant when streaming with rate limiting enabled.

```yaml
burst:
  enabled: false
  p: 0.01
  burst_rate: 10000    # target events/sec during burst
  burst_duration: 10   # seconds
```

---

### Data ops

#### schema_field_nulling
Picks one field in each item and sets it to null. Classic missing-data scenario.

```yaml
schema_field_nulling:
  enabled: true
  p: 0.01
  fields: []   # empty = any leaf field eligible; or specify dotted paths
```

#### truncate
Truncates the serialized JSON - cuts the payload mid-string to produce corrupt/incomplete data. Tests JSON parse error handling.

```yaml
truncate:
  enabled: true
  p: 0.01
  min_items: 1   # min fields to corrupt
  max_items: 3
```

#### schema_bloat
Inflates string fields with extra padding - simulates oversized payloads. Good for testing buffer handling and memory limits.

```yaml
schema_bloat:
  enabled: true
  p: 0.01
  extra_kb: 32         # extra kilobytes to inject
  strategy: insert     # insert | repeat
```

#### duplicate_items
Duplicates elements inside lists in the response. Tests deduplication logic in consumers.

```yaml
duplicate_items:
  enabled: true
  p: 0.01
  max_dups: 1          # extra copies per list
  strategy: adjacent   # adjacent | random
  include_root: true   # also duplicate root-level lists
```

#### list_shuffle
Shuffles every list in the response body. Tests consumers that assume ordered output.

```yaml
list_shuffle:
  enabled: true
  p: 0.01
```

#### encoding_corrupt
Replaces one character in a string field with `U+FFFD` (the Unicode replacement character). Simulates encoding issues - light corruption that won't break JSON parsing but will break downstream string validation.

```yaml
encoding_corrupt:
  enabled: true
  p: 0.01
  fields_to_corrupt: 1   # number of string fields to corrupt
```

#### partial_load
Slices the response list at a random point and returns only part of it - simulates a paginated or interrupted response.

```yaml
partial_load:
  enabled: true
  p: 0.01
```

#### data_drift
Shifts field values according to drift specs - integers get biased, enums get reweighted, floats get jittered. Simulates gradual distribution drift over time, like what you'd see in a model going stale.

```yaml
data_drift:
  enabled: true
  p: 0.01
  max_mutations: 3   # fields to drift per activation
  q: 0.15            # per-field chance to alter value
  max_hits: 3        # times a drift layer can fire before expiring
  fields:
    event_name:
      mode: categorical
      choices: [purchase, login, search, view_item]
      weights_delta:
        purchase: 0.2    # push purchase probability up
        login: -0.1      # push login probability down
      q: 0.25
    event_value:
      mode: numeric
      add: 0.0
      mul: 1.0
      jitter: 1.5
```

---

### Temporal ops

#### time_skew
Shifts numeric timestamp fields (Unix timestamps) forward or backward by up to `max_skew_s` seconds.

```yaml
time_skew:
  enabled: true
  p: 0.01
  max_skew_s: 3600          # max shift in seconds
  direction: both           # past | future | both
  fields: [event_timestamp] # which fields to skew
```

#### schema_time_skew
Same idea but for ISO 8601 formatted datetime strings.

```yaml
schema_time_skew:
  enabled: true
  p: 0.01
  max_skew_s: 900
  direction: both
  fields: [event_timestamp]
```

#### late_arrival
Rewrites timestamp fields to a recent past value - simulates out-of-order events arriving late in a stream.

```yaml
late_arrival:
  enabled: true
  p: 0.01
  min_elapsed_seconds: 10   # only kicks in after the stream has been running this long
  late_window_seconds: 5    # how many seconds back to set the timestamp
```

---

### Schema evolution ops

#### schema_drift
Mutates the structure of items - adds new fields, drops existing ones, renames them, or flattens nested objects. Simulates schema evolution in a producer you don't control.

```yaml
schema_drift:
  enabled: true
  p: 0.01
  max_mutations: 2   # structural changes per activation
  config:
    skip_fields: []  # fields that should never be touched
    mutations:
      add_field: 1.0
      drop_entry: 1.0
      rename_entry: 1.0
      flatten_object: 0.5
    templates:
      maybe_probability: 0.3   # chance new fields are nullable
```

---

### Header ops

#### header_anomaly
Records header anomalies in the response metadata. Tests clients that validate headers.

Patterns: `huge_value` (8KB header value), `non_ascii` (non-ASCII characters), `dup_keys` (duplicate header keys).

```yaml
header_anomaly:
  enabled: true
  p: 0.01
  patterns: [huge_value, non_ascii, dup_keys]
  huge_value_bytes: 8192
  dup_keys_count: 2
```

#### random_header_case
Mutates header values by randomizing their casing (`Content-Type: APPLICATION/JSON`). Some HTTP clients are stricter than they should be about this.

```yaml
random_header_case:
  enabled: true
  p: 0.01
  headers: [content-type]
  mode: random   # random | upper | lower
```

---

## Forcing ops for testing

You don't have to wait for probabilistic activation. Force any op directly via the query param:

```bash
# test null field handling
curl "http://localhost:8000/v1/schemas/smoke/generate?count=20&chaos_ops=schema_field_nulling"

# test combined temporal issues
curl "http://localhost:8000/v1/schemas/ga4/generate?count=50&chaos_ops=late_arrival,schema_time_skew"

# test schema evolution consumer
curl "http://localhost:8000/v1/schemas/smoke/generate?count=10&chaos_ops=schema_drift"

# stress test your error handling
curl "http://localhost:8000/v1/schemas/smoke/generate?chaos_ops=http_error,truncate,schema_field_nulling"
```

Multiple ops can fire on the same request - the budget caps keep it within reason.
