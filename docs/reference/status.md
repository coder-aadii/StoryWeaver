# Implementation Status Matrix

> The canonical statement of what StoryWeaver does today versus what is only designed. Other documents link here instead of restating status.

## Status

Implemented (this document is maintained against the code; see [How to update](../README.md#how-to-update-the-documentation)).

**Legend.** *Implemented* = exists, runs, and has automated tests or a manual verification noted. *Partially implemented* = some pieces exist (interfaces, schema, adapters) but no working end-to-end feature. *Planned* = designed, no code. *Future/Deferred* = intentionally postponed until the production workflow needs it.

Last verified against the repository: 2026-10-01 (initial foundation commit).

## Matrix

| Area | Current State | Status | Relevant Docs | Notes |
| --- | --- | --- | --- | --- |
| FastAPI application | App factory, CORS, `/api/v1` router, structured logging | Implemented | [backend](../architecture/backend-architecture.md) | Sync endpoints; no auth |
| REST CRUD (channels, sources, transcripts, topics, collections, projects, scripts, scenes, assets, renders) | Generic CRUD: list/get/create/patch/delete | Implemented | [api](../api/README.md) | Pagination by `limit`/`offset`; 409 on conflicts/bad FKs |
| API for characters, locations, script/scene versions, project↔source and collection↔video links, chunks | Tables exist; no routes | Planned | [characters](../api/resources/characters.md) | Add when a workflow consumes them |
| Health endpoints (`/health`, `/ready`, `/providers`) | Liveness, DB+pgvector readiness, provider configuration (no secrets) | Implemented | [health](../api/health-and-readiness.md) | |
| Authentication / users | None | Planned | [authentication](../api/authentication.md) | Local single-user; do not expose beyond localhost |
| PostgreSQL schema (17 tables) + Alembic | One migration, up/down/re-up verified, `alembic check` clean | Implemented | [schema](../data/database-schema.md) | Enums as VARCHAR; embedding dim 768 |
| pgvector storage & ANN index | `transcript_chunks.embedding` + HNSW cosine index; NN query tested | Implemented | [vectors](../data/embeddings-and-vector-search.md) | No embedding generation or search API |
| CharacterVersion, visual-style/era entities, tags | Not modelled | Future | [character system](../domains/character-system.md) | Deferred until a consumer exists |
| LLM provider layer | `generate`, `generate_structured` (JSON-schema prompt + 1 retry), adapters: Ollama, Google, OpenRouter, Grok, Claude-compatible; lazy registry | Partially implemented | [providers](../architecture/provider-architecture.md) | Only the Ollama adapter has a mocked-HTTP test; Google/OpenRouter/Grok/Claude-compatible are untested; `generate_structured` tested with a fake provider; none run against live services. Non-HTTP failures unwrapped ([KI-3](#known-issues-and-limitations)) |
| Model routing / fallback / cost tracking | Per-task model *settings* only (`analysis/story/script/classification`) | Planned | [routing](../ai/model-routing.md) | Decision pending |
| Embedding provider layer | Interface + Ollama/Google adapters | Partially implemented | [embeddings](../ai/embeddings.md) | Untested live; no workflow; no dimension check ([KI-6](#known-issues-and-limitations)) |
| Prompts | None (`packages/prompts` is a placeholder) | Planned | [prompting](../ai/prompting-strategy.md) | |
| Source extraction abstraction | `SourceExtractor` → `NormalizedSource`; YouTube URL classification/validation (unit-tested); yt-dlp extractor behind optional extra | Partially implemented | [source library](../domains/source-library.md) | yt-dlp path untested live |
| Channel scan / import / sync | Domain tables only | Planned | [channel ingestion](../domains/channel-ingestion.md) | |
| Transcript extraction & normalization | `Transcriber` interface; faster-whisper adapter (lazy, optional extra); `chunk_segments` (tested). `extract()` returns metadata only; one `text`+`segments` per transcript (raw vs cleaned and raw file location Decision pending); versioning is a target | Partially implemented | [transcripts](../domains/transcript-pipeline.md) | No end-to-end workflow; whisper untested live; [KI-13](#known-issues-and-limitations), [KI-15](#known-issues-and-limitations) |
| Local file/URL/TXT/SRT/VTT import | Not implemented | Planned | [ingestion workflow](../workflows/ingestion-workflow.md) | |
| Semantic research / RAG | Schema only | Planned | [RAG](../ai/rag-strategy.md) | |
| Topic classification, collections | CRUD for topics/collections; no classification, no membership API | Partially implemented | [topics & collections](../domains/topic-and-collection-system.md) | |
| Projects | CRUD + status enum; UI list/create/detail | Implemented (CRUD only) | [projects](../domains/project-system.md) | No pipeline behind the statuses |
| Story analysis / candidates / architecture | None | Planned | [story generation](../domains/story-generation.md) | |
| Script generation & versioning | `Script`/`ScriptVersion` tables; no generation | Planned | [script generation](../domains/script-generation.md) | |
| Storyboard / scene generation | `SceneSpec` schema, `Scene`/`SceneVersion` tables; no generation | Partially implemented | [storyboard](../domains/storyboard-system.md) | |
| Character / visual bible | `Character`, `Location` tables only | Partially implemented | [characters](../domains/character-system.md), [visual](../domains/visual-system.md) | |
| Image generation | `ImageGenerator` interface, ComfyUI **stub** (reachability check only), mock generator (solid PNG) | Partially implemented | [image generation](../domains/image-generation.md) | No real generation; setting `COMFYUI_BASE_URL` selects the stub, whose `generate()` raises ([KI-18](#known-issues-and-limitations)) |
| Voice / TTS | `VoiceProvider` interface; unconfigured provider raises | Partially implemented | [voice](../domains/voice-and-audio.md) | No engine |
| Music, SFX, mixing, ducking, loudness | None | Planned | [music & SFX](../media/music-and-sfx.md) | |
| Subtitles | Per-scene caption text rendered by the Remotion composition | Partially implemented | [subtitles](../domains/subtitle-system.md) | No SRT/VTT, no word-level alignment |
| Timeline builder | `build_timeline` (deterministic start/duration; 2–7 s *estimate* clamp; code, not the LLM, owns duration) | Implemented | [timeline](../domains/timeline-system.md) | Measured audio duration and asset (`image_src`/`audio_src`) resolution not wired ([KI-16](#known-issues-and-limitations)) |
| Remotion composition | `Basic`: gradient bg, image/placeholder, 6 camera movements + static, subtitle, optional audio; sample render verified | Implemented (basic) | [remotion](../media/remotion.md) | No transitions |
| Final render workflow | Manual `make render-sample` only | Planned | [render workflow](../workflows/render-workflow.md) | No project→MP4 pipeline, no FFmpeg code of our own |
| Automated QA | None | Planned | [QA](../domains/quality-assurance.md) | |
| Workflow runner | `LocalRunner` thread pool + `WorkflowRunner` protocol; nothing submits jobs yet | Partially implemented | [workflows](../workflows/workflow-overview.md) | |
| Temporal | Compose profile + `TEMPORAL_ADDRESS` setting; unused | Future | [workflow architecture](../architecture/workflow-architecture.md) | |
| Local storage | `LocalStorage` (traversal-safe, streaming, sha256, size cap), `data/` layout | Implemented (library only) | [storage](../architecture/storage-architecture.md) | Unused by routes; no upload or file-serving endpoint ([KI-9](#known-issues-and-limitations), [KI-17](#known-issues-and-limitations)) |
| MinIO / S3 | Compose profile only | Future | [ADR-008](../decisions/ADR-008-storage-strategy.md) | |
| Web app shell | Next.js 16 pages: dashboard, sources, topics, collections, projects, studio, settings | Implemented | [frontend](../frontend/README.md) | Mostly read-only lists |
| Studio | Placeholder: Remotion Player on a sample timeline + pipeline outline | Partially implemented | [studio](../frontend/studio.md) | Not an editor |
| Tests | pytest, Vitest (web + video) and Playwright suites; counts and how to run them are canonical in [testing strategy](../testing/testing-strategy.md) | Implemented | [testing](../testing/testing-strategy.md) | No CI ([KI-10](#known-issues-and-limitations)) |
| Lint/type checks | ruff, pyright strict, ESLint, tsc, Prettier | Implemented | [quality gates](../testing/quality-gates.md) | Run locally via `make lint` |
| Docker Compose | Postgres (pgvector) + opt-in Temporal/MinIO | Partially implemented | [docker](../operations/docker.md) | Compose path **never run** on the dev machine |
| Docker-free Postgres | `scripts/dev_postgres.py` via `pgserver` | Implemented | [local env](../operations/local-environment.md) | Verified |
| Observability | Structured JSON logs with key-name (substring) redaction — masks `output_tokens` ([KI-2](#known-issues-and-limitations)); no metrics/tracing | Partially implemented | [logging](../operations/logging.md), [monitoring](../operations/monitoring.md) | |
| Backups, deployment, CI/CD | None | Planned | [backups](../operations/backups.md), [deployment](../operations/deployment.md) | |
| Incremental channel sync | Not implemented; no cursor/`last_synced` field | Planned | [channel sync](../workflows/channel-sync-workflow.md) | Needs idempotency, dedup, resumability ([KI-23](#known-issues-and-limitations)) |
| No-media-download strategy | By design: library stores metadata/transcripts/chunks/embeddings; `skip_download` is hard-coded in the extractor; nothing else enforces it | By design (not enforced) | [source library](../domains/source-library.md) | Media download is an optional future capability |
| Source usage tracking / idea reuse | Not modelled (`project_sources` link table only, no endpoint) | Planned | [source library](../domains/source-library.md) | [KI-22](#known-issues-and-limitations) |
| Candidate approval gate before expensive generation | Not implemented; no gate state persisted | Planned | [project system](../domains/project-system.md) | Decision pending: where gate state lives |
| Originality / similarity analysis | None; `transcript_chunks` embeddings are the substrate | Planned | [story generation](../domains/story-generation.md), [data direction](../data/embeddings-and-vector-search.md) | Engineering goal; no legal guarantees |
| Analysis & result caching | None | Planned | [cost strategy](../ai/ai-cost-strategy.md) | |
| Model routing & fallback | Static per-task model settings only | Planned | [routing](../ai/model-routing.md) | Decision pending |
| Cost / token-usage tracking | None (`llm.generated` logs duration; token fields are redacted, [KI-2](#known-issues-and-limitations)) | Planned | [cost strategy](../ai/ai-cost-strategy.md) | |
| Provider failure isolation | Per-entity `status`/`error` columns exist; no workflow uses them; non-HTTP provider errors unwrapped ([KI-3](#known-issues-and-limitations)) | Planned (columns exist) | [retry & recovery](../workflows/retry-and-recovery.md) | |
| Artifact versioning | `ScriptVersion`, `SceneVersion` tables only (no API); no asset versioning | Partially implemented | [workflow overview](../workflows/workflow-overview.md) | Immutability not enforced |
| Artifact dependency tracking & invalidation | None | Planned | [workflow overview](../workflows/workflow-overview.md) | Decision pending |
| Per-scene regeneration | Not implemented; identity/status columns make it possible | Planned | [asset generation](../workflows/asset-generation-workflow.md) | |
| Prompt versioning | Only `script_versions.prompt_version` column; no prompts exist | Planned | [prompting](../ai/prompting-strategy.md) | |
| Studio ten-stage workspace, version history | Placeholder page only | Planned | [studio](../frontend/studio.md) | |

## Verification record

At commit time: `make lint` clean; pytest 35 passed against Postgres 16 + pgvector 0.6.2; Vitest 10 passed; Playwright 2 passed; `next build` succeeded; sample render produced a 6.5 s 1280×720 H.264 MP4.

## Known issues and limitations

> Canonical list of defects and gaps found by auditing the code. Other documents link here (`status.md#known-issues-and-limitations`) instead of restating them. Each is a **code-level** issue documented as-is; none is fixed by the documentation. They are tracked for a separate engineering task. IDs are stable; do not renumber.

| ID | Area | Limitation (current behavior) |
| --- | --- | --- |
| KI-1 | Configuration | `.env.example` ships `STORAGE_ROOT=` (empty). pydantic-settings parses that as `Path('')`, i.e. `.`, so after `cp .env.example .env` storage resolves relative to the process working directory (e.g. `apps/api`), not `<repo>/data`. The `<repo>/data` default applies only when the variable is **unset**. Workaround: delete or comment out the line. |
| KI-2 | Logging | Redaction matches any log key *containing* `key`, `token`, `secret`, `password`, `authorization` or `credential`. `output_tokens` (emitted by `llm.generated`) is therefore logged as `"***"`, as would any key such as `max_tokens`. Token-usage observability cannot work as designed until this changes. Redaction is by key name only; values inside free-text fields (including exception messages logged by the workflow runner) are not scrubbed. |
| KI-3 | Providers | `LLMProvider.generate` wraps only `httpx.HTTPError` into `ProviderError`. A malformed but HTTP-200 response raises `KeyError`/`IndexError`/`JSONDecodeError` unwrapped (e.g. Google returns no `candidates` when safety-blocked). `generate_structured` retries only `ValidationError`/`ValueError`, so those errors abort without retry. |
| KI-4 | API | `PATCH` applies `model_dump(exclude_unset=True)`. An explicit `null` clears nullable columns, and on NOT NULL columns raises an integrity error that is reported as a misleading `409`. The `*Update` schemas carry no length limits, so an over-long value reaches the database and returns `500`. Create schemas do have limits. |
| KI-5 | Health | `GET /health/ready` catches every exception and returns 503 with no log line (nothing records why). The SQLAlchemy engine has no connect timeout configured, so an unreachable host may make the probe slow or hang (not tested). |
| KI-6 | Schema | `Settings.embedding_dimensions` (768) and the `EMBEDDING_DIM` constant that fixes the `vector(768)` column are independent and unchecked; the `embedding_dimensions` setting is not read by any code at all. Changing the setting does not change the column; a mismatched model fails at insert time. |
| KI-7 | Contracts | The zod timeline mirror (`packages/video/src/types.ts`) is hand-maintained and differs from Pydantic: `camera` is required in zod but defaults to `CameraSpec()` in Python; `camera.shot` is a free string in zod but a fixed set in Python. No test compares them. |
| KI-8 | API | `StoryWeaverError` subclasses (`ProviderNotConfiguredError`, `UnsafePathError`, …) are not mapped to HTTP statuses; if raised in a route they would surface as 500. |
| KI-9 | Wiring | No route or service uses `LocalStorage` or `LocalRunner`. `LocalStorage.put` raises a plain `ValueError` over the size cap (not a typed error). There is no upload endpoint and no endpoint serves files from `data/`. |
| KI-10 | Process | No CI exists. All checks run locally (`make lint`, `make test`). |
| KI-11 | Tests | `conftest.engine` clears the settings cache but not the cached `get_engine()`/`get_sessionmaker()`. `test_ready_with_database` passes only because nothing builds the engine earlier; test order matters. |
| KI-12 | Validation | `POST /sources` and `POST /channels` accept any URL string. `classify_youtube_url` is applied only inside the extractor, so API-created rows are not URL-validated. Any future fetch must re-validate. |
| KI-13 | Transcripts | `TranscriptCreate` has no `version` field; the DB default is 1 and `unique(source_video_id, version)` makes a second transcript for a video return `409`. The versioning described for transcripts is a target. `origin` defaults to `unknown` in the DB and `upload` in the API schema. `TranscriptUpdate` can change only `status` and `text`. |
| KI-14 | Sources | An uploaded transcript with no remote origin is not representable without a convention: `source_videos.url` and `external_id` are NOT NULL and `TranscriptCreate` requires a `source_video_id`. |
| KI-15 | Ingestion | `YouTubeExtractor.extract()` returns metadata only (`skip_download` is hard-coded; `NormalizedSource.segments` is never populated). Fetching captions or audio and transcribing is new code, not wiring. Nothing calls the extractor from the API. |
| KI-16 | Timeline | `estimate_duration` clamps to 2–7 s, so narration needing more than 7 s (> ~17 words) is assigned 7 s. It is a fallback estimate and must not be used for final rendering; measured audio length is not yet wired in. `build_timeline` also leaves `image_src`/`audio_src` empty. |
| KI-17 | Rendering | Nothing serves `data/` files over HTTP and `BasicComposition` uses `<Img src>` directly, so generated images could not be shown in the Studio Player or fetched by the renderer today. Asset resolution for render is Decision pending. The sample render has no images. |
| KI-18 | Images | `get_image_generator()` returns the ComfyUI stub whenever `COMFYUI_BASE_URL` is set; its `generate()` raises `ProviderError` ("not implemented"). Setting the variable therefore disables the working mock. |
| KI-19 | Tests | `TEST_DATABASE_URL` is destructive (migrations are run `downgrade base` then `upgrade head`, tables truncated per test). No guard prevents pointing it at a real database. |
| KI-20 | Security | `next dev` binds beyond localhost (it prints a LAN address); the "do not expose beyond localhost" guidance applies to the web dev server as well as the API. |
| KI-21 | Configuration | Next.js reads env files from `apps/web/`, not the repository root. `NEXT_PUBLIC_API_URL` in the root `.env` does not reach the web app; set it in `apps/web/.env.local` or the shell. |
| KI-22 | Data | No storage exists for used ideas / source usage, story candidates, source-analysis results, similarity records, or artifact dependencies (see [data model gaps](../data/story-data-model.md)). |
| KI-23 | Data | `source_videos` has no thumbnail column; `assets.project_id` is NOT NULL so a library-level thumbnail cannot be an `Asset`. No channel-sync cursor/`last_synced` exists. |
| KI-24 | Ingestion | `classify_youtube_url` returns the URL fragment (`@handle`, `channel/UC…`, `c/name`) for channels. Handles can change, so using it as `Channel.external_id` risks duplicates; the canonical channel id must come from extractor output. |
| KI-25 | Build | `next/font/google` fetches fonts at build time, so `next build` needs network access; this conflicts with a fully offline workflow. |
| KI-26 | Docs scope | The root `README.md` still lists system FFmpeg as a Remotion prerequisite, and `.env.example` omits `ENVIRONMENT`, `LOG_LEVEL`, `MAX_UPLOAD_BYTES`, `CORS_ORIGINS` and contains the empty `STORAGE_ROOT=`. Those files are outside `docs/` and have not been changed. |
