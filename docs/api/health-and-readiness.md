# Health and Readiness

> Liveness and readiness endpoints.

## Status

**Implemented** (`apps/api/app/api/v1/health.py`, tested).

## `GET /api/v1/health` — liveness

Always 200 if the process runs; touches no external system.
```json
{"status":"ok","service":"StoryWeaver"}
```

## `GET /api/v1/health/ready` — readiness

Opens a DB connection, runs `SELECT 1`, and checks `pg_extension` for `vector`.
- 200: `{"status":"ready","database":true,"pgvector":true}`
- 503: `{"status":"not_ready","database":false|true,"pgvector":false|true}`

Any exception is swallowed into `false` and **nothing is logged** — the response says *that* it is not ready but not *why* ([KI-5](../reference/status.md#known-issues-and-limitations)). The SQLAlchemy engine has no connect timeout configured, so a probe against an unreachable host may be slow or hang (untested). The web header badge ("API ready / not ready") polls this every 15 s ([frontend/data-fetching](../frontend/data-fetching.md)).

## Design

Importing the app opens no DB connection (engine is lazy), so liveness works with no database — verified by `tests/test_health.py`. Provider availability is separate: [provider-endpoints](provider-endpoints.md). Optional services (Ollama, ComfyUI, Temporal) never affect readiness.

## Not implemented

Migration-version check (readiness does not verify tables exist), queue/worker health, disk-space checks. Related: [operations/monitoring](../operations/monitoring.md).
