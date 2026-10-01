# Debugging

> Where to look when something misbehaves.

## Status

Implemented (techniques); no dedicated tooling beyond logs and health endpoints.

## API

- Logs are JSON on stdout (structlog). Fields commonly present: `level`, `timestamp`, `event`, plus bound context (`workflow_id`, `workflow`, `provider`, `model`, `duration`, `status`, `error`); token counts such as `output_tokens` are logged as numbers, while secret-named keys show as `***`. Uvicorn's access log is plain text, not JSON. See [Logging](../operations/logging.md).
- Interactive docs at `http://localhost:8000/docs`; `/openapi.json` lists 23 paths.
- `GET /api/v1/health` (liveness), `/health/ready` (DB + pgvector, 503 if not; the body's `error` field names the exception type and the log line `health.ready.failed` carries the sanitised detail; the engine has a connect timeout, `DB_CONNECT_TIMEOUT_SECONDS`), `/health/providers` (config only, no secrets). See [Health and readiness](../api/health-and-readiness.md).
- Provider problems: `ProviderNotConfiguredError` means a key/base URL/model is unset (check `/health/providers` and `DEFAULT_LLM_MODEL`). Other failures are `ProviderError` subclasses: `ProviderTimeoutError` (raise `LLM_TIMEOUT_SECONDS` or use a faster model), `ProviderResponseError` (empty, blocked or malformed reply — the message names the reason, e.g. Google `MAX_TOKENS` when a reasoning model spends the whole budget; raise `max_tokens`), or plain `ProviderError` with a `status_code`. Over HTTP these map to 409/504/502 with a stable `code` ([API errors](../api/errors.md)).
- `LocalRunner` background failures are logged as `workflow.failed` with error text; nothing is re-raised to the caller.

## Database

`psql "$DATABASE_URL"` (strip the `+psycopg` driver suffix for psql). Useful: `\dt`, `SELECT * FROM alembic_version;`, `SELECT extname FROM pg_extension;`. See [database development](database-development.md).

## Web

Browser devtools network tab for `http://localhost:8000/api/v1/...`; the UI shows explicit error states (e.g. "Cannot reach the API at …"). CORS allows only `CORS_ORIGINS` (default ports 3000 and 3100).

## Rendering

`pnpm --filter @storyweaver/video studio` for interactive preview; render errors print to the terminal. See [Remotion](../media/remotion.md).

More: [Troubleshooting](troubleshooting.md).
