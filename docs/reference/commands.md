# Command Reference

> Every development command that exists in the repository, with what it does.

## Status

Implemented. Source of truth: the root [`Makefile`](../../Makefile) and each package's `package.json` / `pyproject.toml`.

## Make targets

| Command | Effect |
| --- | --- |
| `make help` | List targets |
| `make setup` | `uv sync` in `apps/api`, `pnpm install`, copy `.env.example` → `.env` if missing |
| `make db-up` / `make db-down` | Docker Compose Postgres (+pgvector) up (waits for healthy) / down. Compose path unverified on the dev machine |
| `make db-up-nodocker` | Docker-free Postgres 16 + pgvector (`scripts/dev_postgres.py`); prints `DATABASE_URL` and `TEST_DATABASE_URL` |
| `make db-migrate` | `alembic upgrade head` |
| `make db-revision m="msg"` | Autogenerate a migration (review it; see [migrations](../development/migrations.md)) |
| `make dev` / `dev-api` / `dev-web` | API on :8000 (reload), web on :3100, or both |
| `make test` / `test-api` / `test-web` | pytest; Vitest for web and video (`test-web` runs both). DB tests skip without `TEST_DATABASE_URL`, which is **destructive** — it must point at a disposable database ([KI-19](status.md#known-issues-and-limitations)) |
| `make e2e` | Playwright (needs the dev stack; see [e2e testing](../testing/e2e-testing.md)) |
| `make lint` | ruff check + format check + pyright; ESLint + tsc (web); tsc (video) |
| `make format` | ruff format/fix; Prettier (web) |
| `make render-sample` | Render `packages/video/sample/timeline.json` → `packages/video/out/sample.mp4` |
| `make schemas` | Export Pydantic JSON Schema to `packages/schemas/` |

## Direct commands

```bash
cd apps/api && uv run uvicorn app.main:app --reload --port 8000
cd apps/api && uv run pytest                 # DB tests skip without TEST_DATABASE_URL
cd apps/api && uv run alembic upgrade head | downgrade base | check
cd apps/api && uv sync --extra ingestion     # yt-dlp
cd apps/api && uv sync --extra transcription # faster-whisper
pnpm --filter @storyweaver/web dev|build|lint|typecheck|test|test:e2e|format|format:check   # build needs network for Google Fonts (KI-25)
pnpm --filter @storyweaver/video studio|render|typecheck|test
docker compose --profile temporal up -d temporal   # opt-in, unused by code
docker compose --profile storage  up -d minio      # opt-in, unused by code
```

See also [setup](../development/setup.md), [troubleshooting](../development/troubleshooting.md).
