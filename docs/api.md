# API Reference

All endpoints, parameters, and response shapes. The API is HTTP for one-shot generation and data retrieval, WebSocket for real-time streaming. Both support chaos injection and deterministic seeding.

Base URL: `http://localhost:8000`

---

## HTTP Endpoints

### Health check

**GET** `/v1/health`

```bash
curl http://localhost:8000/v1/health
```

```json
{"status": "ok", "ts": "2025-01-12T10:30:45.123456Z"}
```

---

### List schemas

**GET** `/v1/schemas`

Returns all schemas currently loaded from the `schemas/` directory.

```bash
curl http://localhost:8000/v1/schemas
```

```json
{"schemas": ["ga4", "smoke"], "count": 2}
```

---

### Generate data

**GET** `/v1/schemas/{name}/generate`

The main endpoint. Generates one or more records from a schema.

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `count` | int | 1 | Number of records to generate (1–1000) |
| `seed` | int | null | Fix the RNG seed for deterministic output |
| `chaos_ops` | string | null | Force specific chaos ops (comma-separated) |
| `include_metadata` | bool | false | Include `_metadata` block in response |
| `persist` | bool | true | Save the dataset for later retrieval |

```bash
# single item
curl http://localhost:8000/v1/schemas/smoke/generate

# batch
curl "http://localhost:8000/v1/schemas/smoke/generate?count=100"

# deterministic - same seed, same output every time
curl "http://localhost:8000/v1/schemas/smoke/generate?seed=42&count=10"

# with chaos
curl "http://localhost:8000/v1/schemas/smoke/generate?count=10&chaos_ops=latency,schema_field_nulling"

# don't persist this one
curl "http://localhost:8000/v1/schemas/smoke/generate?persist=false"

# include generation metadata
curl "http://localhost:8000/v1/schemas/smoke/generate?include_metadata=true"
```

**Response (default):**
```json
{
  "items": [
    {"user_id": "user-042", "age": 34, "email": "john@example.com"},
    {"user_id": "user-017", "age": 28, "email": "jane@example.com"}
  ],
  "count": 2
}
```

**Response with `include_metadata=true`:**
```json
{
  "items": [...],
  "count": 2,
  "_metadata": {
    "schema": "smoke",
    "seed": 42,
    "seed_source": "user_provided",
    "schema_version": "latest",
    "generated_at": "2025-01-12T10:30:45.123456Z",
    "gen_ms": 3.2,
    "e2e_ms": 5.8
  }
}
```

`seed_source` can be `user_provided`, `server_generated`, or `pregen_cache` (when the pre-generation worker served the data).

---

### Retrieve a dataset

**GET** `/v1/data/{id}`

Metadata only - no items.

```bash
curl http://localhost:8000/v1/data/abc123xyz
```

**GET** `/v1/data/{id}/items`

Full dataset with items.

```bash
curl http://localhost:8000/v1/data/abc123xyz/items
```

---

### Delete a dataset

**DELETE** `/v1/data/{id}`

Removes from both Redis and PostgreSQL.

```bash
curl -X DELETE http://localhost:8000/v1/data/abc123xyz
```

---

### Prometheus metrics

**GET** `/metrics`

Standard Prometheus exposition format. Covers HTTP latency, generation rates, chaos op counts, WebSocket connections, persistence writes, and more.

---

## WebSocket Streaming

**WS** `/v1/schemas/{name}/stream`

Real-time streaming - connect, send params, receive items.

### Connection flow

1. Connect to `ws://localhost:8000/v1/schemas/smoke/stream`
2. Send a JSON params message
3. Receive one JSON item per message until done

### Params message

```json
{
  "count": 1000,
  "rate": 50,
  "seed": 42,
  "chaos_ops": "schema_field_nulling,late_arrival"
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `count` | int | 1 | Total items to stream |
| `rate` | float | 1000 | Items per second |
| `seed` | int | null | RNG seed for deterministic output |
| `chaos_ops` | string | null | Force specific chaos ops (comma-separated) |

### Python example

```python
import asyncio
import websockets
import json

async def stream():
    uri = "ws://localhost:8000/v1/schemas/smoke/stream"
    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps({"count": 100, "rate": 10}))
        async for message in ws:
            item = json.loads(message)
            print(item)

asyncio.run(stream())
```

### Stateful field behavior

Schemas using `stateful_timestamp` or `stateful_datetime` maintain a counter per connection. Each record advances the timestamp by the configured `increment`. When connecting without a seed, the pre-generation worker's position is used as the starting point - this keeps time values coherent across HTTP and WebSocket consumers.

---

## Built-in schemas

### smoke

A test schema that exercises every generator type - templates, Faker providers, enums, nested objects, arrays, maybe, one_of. Good for verifying the service is working and for exploring what the engine can do.

### ga4

A Google Analytics 4 event schema. Nested structure with event name, user properties, device info, geo, and event params. More realistic than `smoke` - useful for testing pipelines that consume analytics data.
