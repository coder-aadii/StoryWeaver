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
- 503: `{"status":"not_ready","database":false|true,"pgvector":false|true,"error":"<ExceptionType>"}` (`error` present when a check raised; type only)

Any exception during the check leaves the failing check `false`, adds `"error": "<ExceptionType>"` to the 503 body (type only — no host or user) and writes a `health.ready.failed` log line with the sanitised detail (previously KI-5, resolved in P0). The SQLAlchemy engine has a connect timeout (`DB_CONNECT_TIMEOUT_SECONDS`, default 10 s), so an unreachable host fails within that bound; a hosted database that scales to zero may need a few seconds to wake, and the first probe can report `not_ready`. The web header badge ("API ready / not ready") polls this every 15 s ([frontend/data-fetching](../frontend/data-fetching.md)).

## Design

Importing the app opens no DB connection (engine is lazy), so liveness works with no database — verified by `tests/test_health.py`. Provider availability is separate: [provider-endpoints](provider-endpoints.md). Optional services (Ollama, ComfyUI, Temporal) never affect readiness.

## Not implemented

Migration-version check (readiness does not verify tables exist), queue/worker health, disk-space checks. Related: [operations/monitoring](../operations/monitoring.md).
