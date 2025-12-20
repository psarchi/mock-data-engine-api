# Mock Data Engine API

[![CI](https://github.com/psarchi/mock-data-engine-api/actions/workflows/ci.yml/badge.svg)](https://github.com/psarchi/mock-data-engine-api/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

FastAPI service for generating realistic mock data via declarative YAML schemas. Define data contracts in YAML, generate deterministic or randomized datasets with built-in chaos injection for testing data pipelines, ETL processes, and streaming systems. Includes dual-layer persistence (Redis/PostgreSQL), real-time streaming, and comprehensive observability.

## Status

**Alpha** - API and configuration schemas may change. Not recommended for production use.

## Quick Start

```bash
# Clone and start services
git clone https://github.com/psarchi/mock-data-engine-api.git
cd mock-data-engine-api
make up  # Auto-generates .env from config/*.yaml files

# OR if you have your own .env file:
# make up WITHOUT_ENV=true

# Verify health
curl http://localhost:8000/v1/health
# {"status":"ok","ts":"2025-12-12T10:30:45.123456Z"}
```

**Services:** API (8000), Grafana (3000), Prometheus (9090), Redis (6379), PostgreSQL (5432)

## First Data Generation

```bash
# Generate single item
curl http://localhost:8000/v1/schemas/stream_events/generate

# Response
{
  "event_id": "evt_a3f9b2c1",
  "event_type": "page_view",
  "user_id": "user_8472",
  "timestamp": "2023-06-15T14:32:18Z",
  "properties": {
    "page_url": "/products/shoes",
    "referrer": "https://google.com"
  }
}
```

## Schema Example

Create `schemas/user.yaml`:

```yaml
type: object
fields:
  user_id:
    type: string
    template: "user-{nnnn}"
  email:
    type: string
    string_type: "internet.email"
  age:
    type: int
    min: 18
    max: 90
  is_active:
    type: bool
    p_true: 0.8
  registration_date:
    type: datetime
    start: "2023-01-01T00:00:00Z"
    end: "2023-12-31T23:59:59Z"
    format: "%Y-%m-%dT%H:%M:%SZ"
```

## Basic API Usage

### Generate Data

```bash
# Single item
curl http://localhost:8000/v1/schemas/user/generate

# Batch (100 items)
curl "http://localhost:8000/v1/schemas/user/generate?count=100"

# Deterministic (with seed)
curl "http://localhost:8000/v1/schemas/user/generate?seed=42&count=10"
```

### Retrieve Persisted Data

```bash
# Get metadata only
curl http://localhost:8000/v1/data/{id}

# Get full dataset with items
curl http://localhost:8000/v1/data/{id}/items
```

### List Schemas

```bash
curl http://localhost:8000/v1/schemas
```

### Stream Data

```
ws://localhost:8000/v1/schemas/{schema}/stream
```

Real-time streaming endpoint. Send JSON params `{"count": 100, "rate": 10}` to control volume and delivery rate (items/sec). Supports chaos injection and deterministic seeding via params.

## Advanced Features (Optional)

<details>
<summary><b>Available Generators</b></summary>

- **string**: Templates (`"user-{nnnn}"`), Faker providers, regex patterns
- **int/float**: Range with min/max/step/precision
- **bool**: Probability-based (`p_true`)
- **datetime**: Range with format and timezone
- **enum**: Weighted choices
- **array**: Variable-length lists
- **object**: Nested structures
- **one_of**: Union types
- **select**: Partial object field selection

</details>

<details>
<summary><b>Chaos Engineering</b></summary>

Enable chaos via query param: `?chaos=true`

Configure in `config/default/chaos.yaml`:

```yaml
chaos:
  enabled: true
  budgets:
    max_faults_per_request: 2
  ops:
    latency:
      enabled: true
      p: 0.1
      min_ms: 100
      max_ms: 500
    schema_field_nulling:
      enabled: true
      p: 0.05
    truncate:
      enabled: true
      p: 0.03
```

**Operations:** latency, http_error, http_mismatch, truncate, schema_field_nulling, schema_bloat, duplicate_items, list_shuffle, late_arrival, time_skew, encoding_corrupt, data_drift, schema_drift, burst, partial_load, schema_time_skew, auth_fault, header_anomaly, random_header_case

</details>

<details>
<summary><b>WebSocket Streaming</b></summary>

```python
import asyncio
import websockets
import json

async def stream():
    uri = "ws://localhost:8000/v1/schemas/user/stream"
    async with websockets.connect(uri) as ws:
        params = {"count": 100, "rate": 10}  # 10 items/sec
        await ws.send(json.dumps(params))

        async for message in ws:
            data = json.loads(message)
            print(data)

asyncio.run(stream())
```

</details>

<details>
<summary><b>Persistence</b></summary>

Dual-layer storage:
- **Redis**: Hot cache (24h TTL, 10GB max)
- **PostgreSQL**: Durable storage (30-day retention)

Datasets auto-persist by default. Disable per-request:

```bash
curl "http://localhost:8000/v1/schemas/user/generate?persist=false"
```

</details>

<details>
<summary><b>Pre-Generation</b></summary>

Background workers pre-generate data for high-throughput scenarios. Configure in `config/default/generation.yaml`:

```yaml
pregeneration:
  schemas: [ga4, smoke]  # Schemas to pre-generate
  workers: 4             # Parallel workers
  target_count: 10000    # Items per schema
```

Worker starts automatically with `make up`. Streaming endpoints automatically consume pre-generated data when available, achieving 20k+ items/sec.

</details>

<details>
<summary><b>Observability</b></summary>

- **Metrics**: http://localhost:8000/metrics (Prometheus format)
- **Dashboards**: http://localhost:3000 (Grafana, admin/admin)
- **Logs**: Structured JSON output (configurable in `config/default/server.yaml`)

</details>

## Configuration

Configuration files in `config/default/*.yaml`:

- `server.yaml` - API server, persistence, observability, profiler
- `generation.yaml` - Generator defaults, RNG, temporal modes, pre-generation
- `chaos.yaml` - Chaos operations and budgets

Override defaults by creating `config/*.yaml` files (gitignored).

## Tools

### JSON to YAML Schema Converter

Bootstrap schemas from JSON examples:

```bash
# Single object
curl https://api.example.com/user | python tools/json_to_schema.py > schemas/user.yaml

# Array of samples (infer ranges)
python tools/json_to_schema.py examples.json --infer-arrays --sample-size 100

# From file
python tools/json_to_schema.py example.json -o schemas/user.yaml
```

The tool automatically detects types (int, float, bool, string patterns), email/URL formats, and merges multiple samples to infer realistic min/max ranges. See [tools/README.md](tools/README.md) for details.

## Repository Layout

```
mock-data-engine-api/
├── mock_engine/          # Core engine
│   ├── generators/       # Data generators
│   ├── chaos/           # Chaos operations
│   ├── persistence/     # Redis/PostgreSQL clients
│   ├── pregeneration/   # Background workers
│   └── schema/          # Schema builder and validation
├── server/              # FastAPI application
│   └── routers/         # API endpoints
├── schemas/             # YAML data contracts
├── config/              # Configuration files
│   └── default/         # Default configs
├── tools/               # Developer tools (json_to_schema)
├── containers/          # Docker service configs
├── tests/               # Test suites
└── docker-compose.yaml  # Full stack deployment
```

## License & Disclaimer

This project is licensed under the MIT License. See the LICENSE file for details.

All generated data is entirely synthetic and intended for development and testing purposes only.  
The software is provided "as is", without warranty of any kind. Users are responsible for compliance with applicable laws and regulations.
