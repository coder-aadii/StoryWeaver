# Development setup

What follows was run on Ubuntu 20.04 (Node 22, pnpm 11, uv 0.12). The Docker path is **not verified on this
machine** (Docker is not installed there); the Docker-free path is.

## 1. Tooling

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh     # uv; provides Python 3.12 automatically
corepack enable   # or install pnpm any other way
```

FFmpeg is only needed for rendering; Remotion downloads its own headless Chrome on first render.

## 2. Install

```bash
cp .env.example .env
make setup
```

Optional extras: `cd apps/api && uv sync --extra ingestion` (yt-dlp), `--extra transcription` (faster-whisper).

## 3. Database

**With Docker:** `make db-up` (Postgres 16 + pgvector on host port **5433**, so it will not clash with a local
Postgres on 5432). The default `DATABASE_URL` already points there.

**Without Docker:** `make db-up-nodocker` starts a user-space Postgres 16 with pgvector and prints
`DATABASE_URL` / `TEST_DATABASE_URL`. Export them, or set `DATABASE_URL` in `.env`.

```bash
make db-migrate
```

## 4. Run

```bash
make dev        # API http://localhost:8000 (docs at /docs), web http://localhost:3100
```

Web uses port 3100 (3000 is commonly taken). Set `NEXT_PUBLIC_API_URL` if the API is elsewhere.
Check: `curl localhost:8000/api/v1/health/ready` → `{"status":"ready","database":true,"pgvector":true}`.

## 5. Test and lint

```bash
export TEST_DATABASE_URL=...   # from step 3; without it DB tests are skipped (not failed)
make test
make lint
make e2e
```

Playwright's bundled browser does not support Ubuntu 20.04. On such systems point it at any Chromium, e.g.
Remotion's: `PLAYWRIGHT_CHROMIUM_PATH=$PWD/packages/video/node_modules/.remotion/chrome-headless-shell/linux64/chrome-headless-shell-linux64/chrome-headless-shell make e2e`.
Elsewhere run `pnpm --filter @storyweaver/web exec playwright install chromium` once.

## 6. Render the sample video

```bash
make render-sample     # → packages/video/out/sample.mp4 (git-ignored)
pnpm --filter @storyweaver/video studio   # Remotion Studio preview
```

## Optional services

`docker compose --profile temporal up -d temporal` · `--profile storage up -d minio`. Neither is used by the
code yet.
