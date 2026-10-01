# Troubleshooting

> Known problems and fixes encountered while building the foundation.

## Status

Implemented (observed issues).

| Symptom | Cause | Fix |
| --- | --- | --- |
| `make db-up`: `docker: command not found` | Docker not installed | Install Docker, or `make db-up-nodocker` |
| `/health/ready` → 503 `database:false` | `DATABASE_URL` wrong/DB down (the exception is not logged — [KI-5](../reference/status.md#known-issues-and-limitations)) | Check URL (port 5433 for compose; exported socket URL for Docker-free); start DB; `make db-migrate` |
| `/health/ready` slow or hangs | Unreachable DB host and no connect timeout ([KI-5](../reference/status.md#known-issues-and-limitations)) | Fix `DATABASE_URL`/host; test with `psql` first |
| Files appear under `apps/api/` instead of `data/` | `STORAGE_ROOT=` left empty in `.env` ([KI-1](../reference/status.md#known-issues-and-limitations)) | Delete/comment the line and restart the API |
| Web ignores `NEXT_PUBLIC_API_URL` from `.env` | Next.js reads `apps/web/`, not the repo root ([KI-21](../reference/status.md#known-issues-and-limitations)) | Put it in `apps/web/.env.local` and restart `next dev` |
| `pgvector:false` | Extension missing | Use `pgvector/pgvector:pg16` image or `CREATE EXTENSION vector;`; run migrations |
| DB tests show as skipped | `TEST_DATABASE_URL` unset or unreachable | Export it (disposable DB!) |
| Web: "Cannot reach the API at …" | API not running / wrong `NEXT_PUBLIC_API_URL` / CORS origin | Start API; set `CORS_ORIGINS` to include the web origin |
| Port 3000/5432 busy | Other local services | Web uses 3100, compose uses 5433 by design |
| Python 3.8 errors | System Python too old | Use `uv` (installs 3.12); `cd apps/api && uv sync` |
| `uv: command not found` | `~/.local/bin` not on PATH | The Makefile prepends it; export it in your shell |
| Playwright "does not support chromium on ubuntu20.04" | Unsupported distro | `PLAYWRIGHT_CHROMIUM_PATH=<chromium>`; see [E2E](../testing/e2e-testing.md) |
| Remotion first render slow | Downloads headless Chrome | One-time |
| Remotion Player logs a license notice | Licensing reminder | Owner decision ([README](../../README.md)) |
| `ProviderNotConfiguredError: no model selected` | `DEFAULT_LLM_MODEL` empty | Set it (and per-task models) in `.env` |
| `ProviderNotConfiguredError: yt-dlp is not installed` | Optional extra | `cd apps/api && uv sync --extra ingestion` |
| Next fonts fail offline build | `next/font/google` fetches fonts at build ([KI-25](../reference/status.md#known-issues-and-limitations)) | Needs network once; switching to local fonts is Decision pending |
| `.env` changes ignored | `Settings` cached with `lru_cache` | Restart the API |

See [Debugging](debugging.md) and [Local environment](../operations/local-environment.md).
