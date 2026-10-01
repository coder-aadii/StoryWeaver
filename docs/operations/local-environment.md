# Local Environment

> What runs on a developer machine and how much it costs.

## Status

Implemented.

## Processes

| Process | Command | Port | Required |
| --- | --- | --- | --- |
| PostgreSQL + pgvector | `make db-up` (Docker, unverified) or `make db-up-nodocker` | 5433 on `127.0.0.1` for Compose; **no TCP port** for the Docker-free cluster — it listens on a unix socket in `data/temporary/pgdata` | Yes |
| API (uvicorn `--reload`) | `make dev-api` | 8000 | Yes |
| Web (Next.js dev) | `make dev-web` | 3100 (binds beyond localhost — prints a LAN URL; see [KI-20](../reference/status.md#known-issues-and-limitations)) | For the UI |
| Remotion Studio / render | `pnpm --filter @storyweaver/video studio\|render` | 3000 (Remotion default) | On demand |
| Ollama, ComfyUI, TTS, Temporal, MinIO | external / opt-in | 11434 / configurable | **No** — none are needed to boot |

## Design constraints (target hardware: Ryzen 5 5500U, 16 GB, no GPU)

- Nothing preloads models or opens connections at startup.
- Large media is streamed to disk (`LocalStorage.put` reads 1 MiB chunks); never read whole videos into RAM.
- The only always-on service is Postgres.
- `LocalRunner` uses a 2-thread pool to cap concurrency.

## Data on disk

`data/` (git-ignored; skeleton kept via `.gitkeep`) — see [storage layout](../data/storage-layout.md). `data/temporary/pgdata` holds the Docker-free Postgres cluster. `packages/video/out/` holds renders (git-ignored).

## Verified vs unverified

Which `DATABASE_URL` applies: Compose uses the default (`…@localhost:5433/storyweaver`) from `.env` or the built-in default; the Docker-free helper prints a socket URL (`postgresql+psycopg://postgres@/storyweaver?host=<repo>/data/temporary/pgdata`) that you must **export** or put in `.env`. See the [setup checklist](../development/setup.md#3-database).

Verified: Docker-free Postgres, API, web, tests, Remotion render on Ubuntu 20.04. Unverified: Docker Compose services, macOS/Windows.

See [setup](../development/setup.md), [configuration](configuration.md).
