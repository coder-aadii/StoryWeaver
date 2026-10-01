# Debugging

> Where to look when something misbehaves.

## Status

Implemented (techniques); no dedicated tooling beyond logs and health endpoints.

## API

- Logs are JSON on stdout (structlog). Fields commonly present: `level`, `timestamp`, `event`, plus bound context (`workflow_id`, `workflow`, `provider`, `model`, `duration`, `status`, `error`). Note that `output_tokens` is logged as `"***"` ([KI-2](../reference/status.md#known-issues-and-limitations)) and uvicorn's access log is plain text, not JSON. See [Logging](../operations/logging.md).
- Interactive docs at `http://localhost:8000/docs`; `/openapi.json` lists 23 paths.
- `GET /api/v1/health` (liveness), `/health/ready` (DB + pgvector, 503 if not; the failure reason is **not** logged and there is no connect timeout — [KI-5](../reference/status.md#known-issues-and-limitations)), `/health/providers` (config only, no secrets). See [Health and readiness](../api/health-and-readiness.md).
- Provider problems: `ProviderNotConfiguredError` means a key/base URL/model is unset (check `/health/providers` and `DEFAULT_LLM_MODEL`); `ProviderError` wraps **only** `httpx.HTTPError` failures (only the exception class name is logged). A malformed HTTP-200 response raises an unwrapped `KeyError`/`IndexError`/`JSONDecodeError`, and `generate_structured` does not retry those ([KI-3](../reference/status.md#known-issues-and-limitations)).
- `LocalRunner` background failures are logged as `workflow.failed` with error text; nothing is re-raised to the caller.

## Database

`psql "$DATABASE_URL"` (strip the `+psycopg` driver suffix for psql). Useful: `\dt`, `SELECT * FROM alembic_version;`, `SELECT extname FROM pg_extension;`. See [database development](database-development.md).

## Web

Browser devtools network tab for `http://localhost:8000/api/v1/...`; the UI shows explicit error states (e.g. "Cannot reach the API at …"). CORS allows only `CORS_ORIGINS` (default ports 3000 and 3100).

## Rendering

`pnpm --filter @storyweaver/video studio` for interactive preview; render errors print to the terminal. See [Remotion](../media/remotion.md).

More: [Troubleshooting](troubleshooting.md).
