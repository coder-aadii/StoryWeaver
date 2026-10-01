# Environment Variables

> Operator guidance for the variables the code reads. The table of names, defaults and meanings is not repeated here.

## Status

Implemented. **Canonical table: [environment reference](../reference/environment-reference.md)** (every variable, default and purpose). This page adds handling guidance; [configuration](configuration.md) explains the loading mechanism.

## Which variables are secrets

Treat as secrets (never commit, never log, never send to the browser): `GOOGLE_AI_API_KEY`, `GROK_API_KEY`, `OPENROUTER_API_KEY`, `ANTHROPIC_API_KEY`, and any URL that embeds a password — `DATABASE_URL`, `TEST_DATABASE_URL`, plus `POSTGRES_PASSWORD` and `MINIO_ROOT_PASSWORD` for Compose. Everything else (base URLs, model names, ports, `LOG_LEVEL`) is non-secret. See [secrets](../security/secrets.md).

## Where each variable is read

| Consumer | Variables | Source |
| --- | --- | --- |
| API / Alembic (`Settings`) | all provider, model, storage, database, CORS and logging variables | process environment, then repository-root `.env` |
| pytest | `TEST_DATABASE_URL` (read with `os.environ`, **not** via `Settings`) | environment only. **Destructive** — see [integration testing](../testing/integration-testing.md) ([KI-19](../reference/status.md#known-issues-and-limitations)) |
| Docker Compose | `POSTGRES_*`, `MINIO_ROOT_*` | root `.env` / environment |
| Web (Next.js) | `NEXT_PUBLIC_API_URL` (baked into the client bundle at build/dev start) | **`apps/web/.env.local` or the shell — not the repository-root `.env`** ([KI-21](../reference/status.md#known-issues-and-limitations)) |
| Playwright | `PLAYWRIGHT_CHROMIUM_PATH` | environment |

## Handling rules

- Restart the API after changing `.env` (`get_settings()` is cached).
- An **empty** value is not the same as an **unset** one; leave a variable out entirely if you want its default. In particular remove `STORAGE_ROOT=` from a copied `.env` ([KI-1](../reference/status.md#known-issues-and-limitations)).
- `.env.example` is incomplete: it omits `ENVIRONMENT`, `LOG_LEVEL`, `MAX_UPLOAD_BYTES` and `CORS_ORIGINS` ([KI-26](../reference/status.md#known-issues-and-limitations)); they work when set.
- `CORS_ORIGINS` must be a JSON array (e.g. `["http://localhost:3100"]`).
- `EMBEDDING_DIMENSIONS` does not change the database column ([KI-6](../reference/status.md#known-issues-and-limitations)).
- Never commit `.env` ([secrets](../security/secrets.md)).
