# Changelog

## [0.0.2]

### Entity correlation (`bound_to` / `linked_to`)

Anchor a field and any number of sibling fields to it — same anchor value always produces the same correlated values, across requests and across time. Backed by Redis.

- `bound_to: <anchor_field>` on any leaf generator
- `linked_to` is an alias — identical behavior
- Anchor field must be declared before the fields that reference it
- Cross-schema correlation: `bound_to_schema` + optional `bound_to_revision` to pin a specific schema version
- Correlated values survive restarts — cached until Redis is flushed

### CI / code quality

- Fixed all lint errors (ruff): unused imports, bare `except`, f-strings without placeholders, module-level imports after `sys.path` manipulation
- Fixed all mypy errors: corrected `# type: ignore` error codes, added missing annotations across generators, chaos ops, persistence, and server layers
- Added `httpx` and `websocket-client` to `requirements.txt` (were missing, broke integration test collection)
- Smoke tests now gracefully skip pool-consumer schemas when Redis is unavailable (`PoolEmptyError` -> `pytest.skip`)
- Fixed `schema_bloat`: `need = max(8, need)` was a bare expression (result discarded); corrected to assignment
- Fixed `truncate`: renamed shadowed `desc` variable to `desc_roots` in the root-items branch

### Referential integrity (`pool` / `depends_on_pool`)

Make foreign keys point to real records. Source schemas push generated IDs (plus any sibling fields) into a Redis SET; downstream schemas sample from that set.

- `pool: [sibling_fields]` on the anchor field of the source schema
- `depends_on_pool: <schema_name>` on any FK field in a downstream schema
- Multiple fields referencing the same pool source all read from the same sampled record — one Redis call per pool per generation
- `PoolEmptyError` → HTTP 422 with a clear message when the source pool hasn't been populated yet
- `SchemaConfigError` → HTTP 422 when a downstream field references a key not stored in the pool record
- Admin endpoints: `GET /v1/admin/pools/{schema}`, `DELETE /v1/admin/pools/{schema}`, `DELETE /v1/admin/pools/`

## [0.0.1]

- Initial public release
