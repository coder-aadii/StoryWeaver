# StoryWeaver

> **From source to story to video.**

StoryWeaver is a local-first, AI-assisted story-to-video production engine. The long-term pipeline turns a
source (YouTube URL, transcript, …) into an original script, storyboard, illustrations, narration and a
rendered MP4 — using generated illustrations with camera movement, transitions, voice, music and subtitles
rather than expensive per-scene AI video.

## Current status

This repository is a **foundation**. What exists and is verified, and what does not:

| Area | State |
| --- | --- |
| FastAPI app, `/api/v1` CRUD for 10 resources, health/readiness/provider endpoints | Implemented, tested |
| PostgreSQL + pgvector schema (17 tables) with Alembic migration | Implemented, tested |
| Provider interfaces: LLM (Ollama, Google, OpenRouter, Grok, Claude-compatible), embeddings, image (ComfyUI stub + mock), voice, transcription (faster-whisper), source extraction (YouTube/yt-dlp) | Interfaces and thin adapters. LLM adapters are unit-tested against mocked HTTP only; **not exercised against real services** |
| Local workflow runner, deterministic timeline builder, secure local storage | Implemented, tested |
| Next.js app shell (dashboard, sources, topics, collections, projects, studio, settings) | Implemented, tested |
| Remotion `Basic` composition: timeline JSON → MP4 | Implemented; sample render verified |
| Channel import, transcript extraction, analysis, story/script/storyboard generation, image/voice generation, QA, real rendering workflow, Temporal, MinIO, auth | **Not implemented** (planned) |

## Architecture

One FastAPI application with modular domain packages — not microservices.

```text
apps/web   Next.js (App Router) UI ──HTTP──▶ apps/api  FastAPI
                                              ├─ ingestion/     SourceExtractor → NormalizedSource, transcription
                                              ├─ intelligence/  LLM + embedding provider adapters (lazy registry)
                                              ├─ story/ visual/ voice/ video/ quality/
                                              ├─ workflows/     WorkflowRunner (local now, Temporal later)
                                              └─ models/ db/    SQLAlchemy + Alembic ─▶ PostgreSQL + pgvector
packages/video  Remotion compositions (timeline JSON → video), used by web (Player) and the renderer
data/           Local file storage (git-ignored); the DB stores metadata only
```

Principles: local-first; provider independence; **AI decides content, code decides timing/rendering**;
structured schemas everywhere; per-scene identity so one scene can be regenerated; versioned scripts/scenes.
Details: [`docs/architecture/overview.md`](docs/architecture/overview.md),
[`data-flow.md`](docs/architecture/data-flow.md), [`ADR-001`](docs/decisions/ADR-001-stack.md).

## Stack

Python 3.12 · FastAPI · Pydantic · SQLAlchemy 2 · Alembic · uv — PostgreSQL 16 + pgvector —
Next.js 16 · React 19 · TypeScript (strict) · Tailwind 4 · shadcn/ui · Zustand · TanStack Query —
Remotion 4 (bundles its own ffmpeg) — pytest · ruff · pyright · Vitest · Playwright · ESLint · Prettier.

## Prerequisites

Node ≥ 20 and pnpm, [uv](https://docs.astral.sh/uv/) (installs Python 3.12 for you), and **either** Docker **or**
the Docker-free Postgres helper below. A system FFmpeg is **not** required: Remotion bundles its own
`ffmpeg`/`ffprobe` and downloads a headless Chrome on first render (install FFmpeg only if you want to probe
output files yourself). No GPU, Ollama, ComfyUI or cloud key is needed to boot.

## Quick start

```bash
cp .env.example .env
make setup                  # uv sync + pnpm install
make db-up                  # Docker: Postgres 16 + pgvector on :5433
#   no Docker?  make db-up-nodocker   (prints DATABASE_URL; export it)
make db-migrate
make dev                    # API :8000, web :3100
```

Open <http://localhost:3100>. API docs: <http://localhost:8000/docs>. Full walkthrough and
troubleshooting: [`docs/development/setup.md`](docs/development/setup.md).

## Commands

| Command | What it does |
| --- | --- |
| `make setup` | Install Python + Node dependencies, create `.env` |
| `make db-up` / `make db-down` | Start / stop Postgres via Docker Compose |
| `make db-up-nodocker` | Postgres + pgvector without Docker (via `pgserver`) |
| `make db-migrate` / `make db-revision m="msg"` | Apply / autogenerate Alembic migrations |
| `make dev` (`dev-api`, `dev-web`) | Run API and/or web with reload |
| `make test` (`test-api`, `test-web`) | pytest, Vitest. DB tests need `TEST_DATABASE_URL`, else they skip |
| `make e2e` | Playwright end-to-end (needs the dev stack) |
| `make lint` / `make format` | ruff + pyright + ESLint + tsc / ruff format + Prettier |
| `make render-sample` | Render `packages/video/sample/timeline.json` to `packages/video/out/sample.mp4` |
| `make schemas` | Regenerate JSON Schema into `packages/schemas` |

## Environment variables

See [`.env.example`](.env.example). All AI providers are optional; nothing fails at startup when they are
unset. Model names are configuration (`DEFAULT_LLM_MODEL`, `SCRIPT_LLM_MODEL`, …), never hard-coded.
Keys are read by the API only and never sent to the browser; `GET /api/v1/health/providers` reports
configured/available without exposing them. The web app reads its own `apps/web/.env.local` (see
`apps/web/.env.example`), not the root `.env`. The full variable list is in
[`docs/reference/environment-reference.md`](docs/reference/environment-reference.md).

## Project structure

```text
apps/api/        FastAPI app (app/), Alembic (alembic/), tests (tests/)
apps/web/        Next.js UI, Vitest unit tests, Playwright e2e (e2e/)
packages/video/  Remotion compositions + sample timeline
packages/schemas JSON Schema exported from Pydantic;  packages/prompts, packages/config: placeholders
infrastructure/  Postgres init SQL; temporal/docker/scripts placeholders
services/        Intentionally empty (see services/README.md)
docs/            architecture, decisions (ADRs), development
data/            Local storage skeleton (contents git-ignored)
```

## Notes

- **Remotion licensing:** Remotion is free for individuals and small teams but requires a company license
  above a size threshold. Check <https://remotion.dev/license>; the Player logs a reminder until you set
  `acknowledgeRemotionLicense`, which we have deliberately left for you to decide.
- **YouTube ingestion** uses `yt-dlp` (optional extra) and should only be used on content you are
  authorised to use.

## Roadmap

1. Source ingestion: single video → transcript, then channel scan/import workflow.
2. Chunking + embeddings + semantic search (pgvector schema is ready).
3. Content analysis → story architecture → script (versioned).
4. Storyboard, character/visual bible, scene regeneration.
5. Image (ComfyUI) and voice (Piper/Kokoro) generation, subtitle alignment, music/SFX.
6. Timeline → Remotion/FFmpeg render workflow, automated QA.
7. Durable workflows on Temporal; optional MinIO storage.
