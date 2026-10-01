# Development Setup

> Get StoryWeaver running on a developer machine, with commands that were actually executed.

## Status

Implemented. Verified on Ubuntu 20.04 (Node 22, pnpm 11, uv 0.12). The Docker path (`make db-up`) is **unverified** — Docker was not installed on that machine. The Docker-free path (`make db-up-nodocker`) was verified.

## 1. Tooling

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh     # uv; provides Python 3.12 automatically
corepack enable                                      # or install pnpm another way
```

System FFmpeg is **not** required to render: Remotion ships its own `ffmpeg`/`ffprobe` and downloads a headless Chrome on first render. Install FFmpeg only if you want to probe output files yourself (`ffprobe`). No StoryWeaver code invokes FFmpeg directly ([FFmpeg](../media/ffmpeg.md)).

## 2. Install

```bash
make setup          # uv sync (apps/api) + pnpm install + copies .env.example to .env if .env is missing
```

(If you prefer to copy the file yourself, `cp .env.example .env` is equivalent to that last step.) The shipped `.env.example` has the optional application variables (`ENVIRONMENT`, `LOG_LEVEL`, `MAX_UPLOAD_BYTES`, `CORS_ORIGINS`) commented out with their defaults and no longer sets `STORAGE_ROOT` (an empty value now means unset anyway). For the web app, copy `apps/web/.env.example` to `apps/web/.env.local` only if the API is not at `http://localhost:8000`; see the [environment reference](../reference/environment-reference.md).

Optional extras (not needed to boot): `cd apps/api && uv sync --extra ingestion` (yt-dlp), `--extra transcription` (faster-whisper).

## 3. Database

- **With Docker (unverified here):** `make db-up` — `pgvector/pgvector:pg16` on host port **5433** so it does not clash with a local Postgres on 5432. The default `DATABASE_URL` already points there. See [Docker](../operations/docker.md).
- **Without Docker (verified):** `make db-up-nodocker` runs `scripts/dev_postgres.py` (user-space Postgres 16 + pgvector via the `pgserver` wheel, data in `data/temporary/pgdata`). It prints `DATABASE_URL` and `TEST_DATABASE_URL`; export them or put `DATABASE_URL` in `.env`.

```bash
make db-migrate
```

**First-run checklist — which `DATABASE_URL` does the API use?**

| Step | Docker (unverified) | Docker-free (verified) |
| --- | --- | --- |
| Start DB | `make db-up` | `make db-up-nodocker` (prints two URLs) |
| `DATABASE_URL` | the built-in default (`postgresql+psycopg://storyweaver:storyweaver@localhost:5433/storyweaver`) works with no setup; override in `.env` only if you changed `POSTGRES_*` | **must be provided**: `export DATABASE_URL=...` (the printed socket URL) in every shell that runs `make db-migrate`/`make dev-api`, or put it in `.env` |
| Migrate | `make db-migrate` | `make db-migrate` (same shell/`.env`) |
| Test DB | `TEST_DATABASE_URL=postgresql+psycopg://storyweaver:storyweaver@localhost:5433/storyweaver_test` — create it first (e.g. `docker compose exec postgres createdb -U storyweaver storyweaver_test`; unverified) | the second printed URL (`…/storyweaver_test?host=<repo>/data/temporary/pgdata`) |
| Check | `curl localhost:8000/api/v1/health/ready` | same |

The Docker-free database lives only in `data/temporary/pgdata` — see [backups](../operations/backups.md) before deleting that directory.

## 4. Run

```bash
make dev       # API http://localhost:8000 (/docs), web http://localhost:3100
```

Web uses 3100 because 3000 is often occupied. If the API lives elsewhere set `NEXT_PUBLIC_API_URL` in **`apps/web/.env.local`** (or the shell; see `apps/web/.env.example`); Next.js does not read the repository-root `.env`. Both dev servers bind to `127.0.0.1` (`make dev-api` passes `--host 127.0.0.1`; the web scripts pass `-H 127.0.0.1`), and the API allows the `http://localhost:3100` and `http://127.0.0.1:3100` origins. Check readiness:

```bash
curl localhost:8000/api/v1/health/ready   # {"status":"ready","database":true,"pgvector":true}
```

## 5. Test and lint

```bash
export TEST_DATABASE_URL=...   # from step 3; without it DB tests are skipped, not failed
make test
make lint
make e2e                        # needs the dev stack running
```

**`TEST_DATABASE_URL` is destructive**: the test fixture downgrades the schema to base, re-migrates it, and truncates every table between tests. It refuses a database whose name does not end in `_test` or that equals `DATABASE_URL` (checked before any DDL), but still use a dedicated `storyweaver_test` database. Test counts and layers: [testing strategy](../testing/testing-strategy.md).

Playwright's bundled browser is unsupported on Ubuntu 20.04; set `PLAYWRIGHT_CHROMIUM_PATH` to any Chromium (see [E2E testing](../testing/e2e-testing.md)).

## 6. Render the sample video

```bash
make render-sample                          # → packages/video/out/sample.mp4 (git-ignored)
pnpm --filter @storyweaver/video studio     # Remotion Studio
```

## Optional services

`docker compose --profile temporal up -d temporal`, `docker compose --profile storage up -d minio`. Neither is used by the code yet — see [Workflow architecture](../architecture/workflow-architecture.md).

## Next

[Development workflow](development-workflow.md) · [Troubleshooting](troubleshooting.md) · [Commands reference](../reference/commands.md)

> Working as an AI coding agent? Read [AI agent guide](ai-agent-guide.md) first.
