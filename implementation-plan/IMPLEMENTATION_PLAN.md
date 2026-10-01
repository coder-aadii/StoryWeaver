# StoryWeaver Implementation Plan

> The engineering execution roadmap: how to build the remaining StoryWeaver product from the current codebase — in what order, with which tasks, dependencies, migrations, APIs, UI, workflows, tests and acceptance criteria.

## Status

Planned. This is a plan, not a description of implemented behavior. Nothing in `implementation-plan/` has been built. **Current state is defined by the code and by [`docs/reference/status.md`](../docs/reference/status.md)**; this plan uses the same status vocabulary (*Implemented*, *Partially implemented*, *Planned*, *Future*) and the same term *Decision pending*.

`docs/` answers "what is StoryWeaver and how is it designed". This folder answers "what do we build next, and how do we know it is done". It links to `docs/` instead of restating design.

## 1. Purpose

Take StoryWeaver from a verified foundation (API + schema + provider interfaces + web shell + one Remotion composition) to a usable end-to-end MVP: **one source → understood → a story chosen by the user → script → storyboard → illustrations → narration → rendered MP4**, with every intermediate artifact inspectable, versioned and individually regenerable.

## 2. How to use this plan

- **Coding agents:** read [`docs/development/ai-agent-guide.md`](../docs/development/ai-agent-guide.md) first, then this file, then the detail file for the phase you are about to work on. **Inspect the actual code before implementing** — file lists here are *likely* locations, marked `NEW` / `MODIFY`, not instructions to edit blindly. Never expand a task beyond its phase.
- **Order matters.** Phases have explicit `Depends on`. Do not start a phase whose prerequisites' acceptance criteria are unmet.
- **Task IDs** (`P1-T4`) are stable references for commits, PRs and discussion. Acceptance criteria are written to be checkable by a test or a command.
- **Do not commit or push** unless the user asks (agent-guide rule 20).
- **Docs follow code:** each phase ends by updating [`status.md`](../docs/reference/status.md) and the affected docs (the "Docs" line in each phase).

| File | Contents |
| --- | --- |
| [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) | This file: baseline, principles, roadmap, MVP, decisions, definition of done |
| [`01-foundation.md`](01-foundation.md) | P0 — hardening, known-issue triage, shared engineering conventions |
| [`02-source-library.md`](02-source-library.md) | P1 — Source Library V1 (first product milestone) |
| [`03-intelligence-runtime-and-understanding.md`](03-intelligence-runtime-and-understanding.md) | P2 — jobs, routing, cache, usage, prompts; P3 — source understanding |
| [`04-story-script-storyboard.md`](04-story-script-storyboard.md) | P4 — candidates, approval, architecture; P5 — script, validation, storyboard |
| [`versioning-and-invalidation.md`](versioning-and-invalidation.md) | The artifact version / staleness design used by P4–P9 |
| [`05-visuals-and-audio.md`](05-visuals-and-audio.md) | P6 — visuals; P7 — voice, audio, subtitles |
| [`06-timeline-render-qa.md`](06-timeline-render-qa.md) | P8 — timeline, render, deterministic QA |
| [`07-studio.md`](07-studio.md) | P9 — Studio workflow |
| [`08-hardening-and-post-mvp.md`](08-hardening-and-post-mvp.md) | P10 — MVP hardening; P11–P13 post-MVP roadmap |

## 3. Current baseline (verified against the repository)

Counted from the working tree, not from documentation:

- **Backend** (`apps/api/app`, ~1,750 lines of Python + ~340 lines of tests): FastAPI app; generic CRUD router factory (`api/crud.py`) wired to 10 resources in `api/v1/router.py`; health endpoints; 17 SQLAlchemy tables in `models/domain.py` with one Alembic migration; provider interfaces and adapters under `intelligence/providers/`; `ingestion/` (YouTube URL classification, optional yt-dlp extractor, `Transcriber` interface + faster-whisper adapter, `chunk_segments`); `visual/base.py` (ComfyUI **stub**, mock generator); `voice/base.py` (interface only); `video/timeline.py` (`build_timeline`); `workflows/runner.py` (`LocalRunner` — **nothing submits jobs**); `core/storage.py` (`LocalStorage` — **unused by any route**).
- **Not present at all:** any prompt, any use of an LLM by application code, any workflow function, any service layer between routes and tables, any file upload or file-serving route, any job/run table, any usage/cost record, any approval or dependency state, `story/` and `quality/` are docstring-only.
- **Web** (`apps/web/src`): app shell + 11 routes; read-only resource lists; one mutation (create project); `/studio` is a placeholder (Remotion Player on a sample timeline). No Zustand state beyond `sidebarOpen`.
- **Video** (`packages/video`): one composition `Basic` (image/placeholder, 6 camera movements + static, one subtitle per scene, optional audio); no transitions; assets referenced by raw `src`.
- **Tests:** 35 pytest (DB tests need `TEST_DATABASE_URL`), 10 Vitest, 2 Playwright — canonical counts in [`docs/testing/testing-strategy.md`](../docs/testing/testing-strategy.md). No CI.
- **Environment constraints observed on the original dev machine:** CPU-only (Ryzen 5 5500U, 16 GB), no GPU, no Ollama installed, no Docker (the Docker-free Postgres helper is the verified path), Python 3.12 via `uv`, Node 22, pnpm. **Local model speed and image/TTS feasibility on this hardware are unmeasured** — phases P2, P6, P7 start with a measured spike rather than an assumption.

Code-level defects are catalogued in [`docs/reference/status.md#known-issues-and-limitations`](../docs/reference/status.md#known-issues-and-limitations) (KI-1…KI-26); [`01-foundation.md`](01-foundation.md) assigns each to a phase.

## 4. Implementation principles

1. **AI decides content; deterministic code decides execution** ([ADR-004](../docs/decisions/ADR-004-ai-vs-deterministic-responsibilities.md)). Every phase lists both sides; a model never produces IDs, durations, timestamps, paths or statuses.
2. **Staged and gated.** Cheap analysis first; the user approves a story candidate before script generation, and a storyboard before image/voice generation ([cost strategy](../docs/ai/ai-cost-strategy.md)). Gates are *persisted* and *checked by workflow preconditions*, never UI-only.
3. **Reuse before invent.** Extend `Script`/`ScriptVersion`, `Scene`/`SceneVersion`, `Asset`, `Render`, `Character`, `Location`, `SceneSpec`, `Timeline`, `NormalizedSource`, the provider ABCs and the registry. New tables only where [decision D3](#7-technical-decisions-recommended-defaults) says so.
4. **Modular monolith, local filesystem, Postgres + pgvector** ([ADR-005](../docs/decisions/ADR-005-postgres-pgvector.md), [ADR-006](../docs/decisions/ADR-006-modular-monolith.md)). No microservices, Kubernetes, separate vector DB, Temporal, MinIO, auth or billing in the MVP.
5. **Provider independence.** Domain code calls `LLMProvider`/`EmbeddingProvider`/`ImageGenerator`/`VoiceProvider` via the registry and *task names*; model ids come from settings. Provider names in this plan are examples, never commitments.
6. **Every phase is independently verifiable** with fakes/mocks first, real providers second. A phase is not "done" because a real model produced something once; it is done when its acceptance criteria pass reproducibly.
7. **Idempotent, retryable, resumable.** Every operation has an idempotency key ([table](../docs/workflows/retry-and-recovery.md)) and writes `status` + `error` to its entity.
8. **Honest status.** Never mark external-provider integration "tested" unless a test or recorded manual run proves it; mocks are labelled mocks.

## 5. Dependency and order strategy

The conceptual pipeline is *not* the build order. Build order is driven by what unblocks validation and what is cheapest to get wrong:

1. **P0 first** — a few defects would corrupt later work (silent storage in the wrong directory, unwrapped provider errors, destructive test DB, no URL validation, token logging masked), and the **Remotion asset-resolution spike** (KI-17) fixes the `Timeline` contract that P5–P8 depend on. Cheap now, expensive later.
2. **P1 Source Library V1 before any AI** — it needs no model, is fully testable offline, and produces the input every later stage consumes.
3. **P2 before P3** — all AI stages share one runtime (persisted jobs, routing, cache, usage records, prompt registry). Building it once, with a fake provider, avoids five divergent ad-hoc call sites.
4. **P3→P4→P5 strictly sequential** — each consumes the previous artifact; each can be validated with a fake provider and recorded fixtures before spending tokens.
5. **Versioning/invalidation core lands in P5**, because scripts and scenes are the first versioned artifacts; later phases only add artifact kinds ([design](versioning-and-invalidation.md)).
6. **P6 (visuals) and P7 (audio) are independent** after P5 and can proceed in parallel; both are the first *expensive* stages and are gated behind storyboard approval.
7. **P8 (render) can be built and tested early on fixtures** (mock images + generated WAV) as soon as the P0 spike lands — only the *content* waits for P6/P7.
8. **Studio (P9) is built incrementally**: each phase ships a minimal stage view for its own artifacts (so every phase is demonstrable); P9 unifies navigation, version history, regeneration and dependency display.
9. **Library expansion (P11: channel import/sync, embeddings, semantic search) is deliberately after the MVP core.** It depends only on P1+P2 and may be scheduled earlier if wanted, but a single 30-minute transcript fits a strong model's context and a map-reduce for smaller ones, so the story value is proven without it.

## 6. Master roadmap

`Status` is the state of the capability **today**, in the canonical vocabulary.

| Phase | Capability | Status | Depends on | Outcome / Checkpoint |
| --- | --- | --- | --- | --- |
| **P0** | Foundation hardening, defect triage, render-contract spike | Partially implemented | — | **A** — foundation trustworthy; render asset path decided |
| **P1** | **Source Library V1**: add source (YouTube URL or transcript upload) → metadata → transcript → normalize → chunk → persist → dedupe → search → usage | Partially implemented | P0 | **B** — a source is added once and is searchable and reusable |
| **P2** | Intelligence runtime: persisted jobs, routing, cache, usage/cost records, prompt registry, structured-output hardening | Partially implemented (adapters only) | P0 | **C0** — any AI stage can be built on one tested runtime |
| **P3** | Source understanding: facts/events/entities/themes + narrative opportunities | Planned | P1, P2 | **C** — inspectable, cached analysis of a source |
| **P4** | Story candidates → **user approval gate** → story architecture | Planned | P3 | **D** — user selects a story; architecture persisted |
| **P5** | Script + validation + storyboard (scenes/shots) + versioning core | Partially implemented (tables only) | P4 | **E** — approved storyboard with versioned scenes |
| **P6** | Visual Bible, character consistency, image generation, asset management, per-scene regeneration | Partially implemented (interfaces/stub) | P5 | **F** — an image per approved scene |
| **P7** | Voice, audio processing, measured durations, subtitles | Partially implemented (interface) | P5 | **G** — narration + subtitles with measured timing |
| **P8** | Timeline v2, Remotion render pipeline, deterministic QA | Partially implemented | P6, P7 (fixtures earlier) | **H** — project → MP4, end to end |
| **P9** | Studio: 10-stage workflow, versions, approvals, regeneration, dependencies | Partially implemented (placeholder) | P5 incremental, P8 | **I** — a user drives the whole pipeline from the UI |
| **P10** | MVP hardening: failure recovery, performance, CI, security pass, docs | Planned | P1–P9 | **J** — MVP |
| P11 | Library expansion: channel scan/import/sync, embeddings, semantic search, multi-source | Planned | P1, P2 | post-MVP |
| P12 | Advanced QA, originality/similarity, richer consistency, transitions | Planned | MVP | post-MVP |
| P13 | Platform: Temporal, MinIO, auth, cloud rendering, deployment | Future | MVP | post-MVP |

### Checkpoints (objective)

| | Checkpoint | Verified by |
| --- | --- | --- |
| A | Foundation operational | `make lint` + `make test` (with DB) green in a fresh clone; blocking KIs closed; fixture render with real image + WAV produces an MP4 whose frame shows the image |
| B | Source Library V1 usable | From the UI: add a YouTube URL *and* upload a transcript; both appear once (re-adding is a no-op), are searchable by keyword, show usage; failures show a retryable error; no media downloaded |
| C0 | Intelligence runtime | A fake-provider workflow runs as a persisted job, survives restart reconciliation, is cached on rerun (0 provider calls), records usage; real provider call works when configured |
| C | Source intelligence usable | One source → persisted, schema-valid analysis + opportunities; second run is a cache hit; analysis is editable |
| D | Story generation usable | Candidates shown; nothing downstream runs until the user approves one; approval persisted |
| E | Script + storyboard usable | Script v1 validated; storyboard of scenes/shots as `SceneVersion` rows; editing creates v2; staleness computed correctly |
| F | Visual generation usable | Every approved scene has an image asset (real or mock-labelled); one scene regenerates alone; consistency inputs recorded |
| G | Audio + timeline inputs usable | Every scene has a WAV with *measured* duration; subtitles timed deterministically; clipping check passes |
| H | End-to-end rendering usable | `POST /projects/{id}/renders` → MP4 with deterministic timeline JSON; QA report persisted; re-render with unchanged inputs reuses/recreates identically |
| I | Studio usable | Full flow driven from the UI incl. approvals, edit, regenerate-one-scene, version history, error display |
| J | MVP hardened | Failure-injection suite passes; 10 consecutive end-to-end runs on fixtures succeed; docs/status updated |

## 7. Technical decisions (recommended defaults)

These resolve the "Decision pending" items the plan depends on. They are **recommendations**; each phase file cites the decision it relies on. Changing one requires an ADR ([`docs/decisions/`](../docs/decisions/README.md)) and updating dependent phases.

| ID | Decision | Recommended default | Alternatives / notes |
| --- | --- | --- | --- |
| D1 | Job state | New table `workflow_runs` (kind, subject, status, `idempotency_key` unique, params, progress, attempts, error, timestamps). **Created by P1** (full D1 columns + a thin `RunService`, first used by `source.add`); **P2 extends it** (ALTER-only: `project_id`, `result`, `max_attempts`, cancel) and builds the generic runtime. `LocalRunner` executes; startup reconciles `running`→`interrupted`. Replaces ad-hoc status polling | Temporal later (P13) behind the same `WorkflowRunner` protocol |
| D2 | AI call records & cache | New table `llm_calls` (task, provider, model, prompt name+version, `input_hash`, tokens, duration, status, error, cost estimate, `response` JSONB, run id). Cache = lookup by `(task, provider, model, prompt_name, prompt_version, request_hash)` (a superset of the originally proposed key, to avoid cross-prompt/provider collisions). `request_hash` = hash of the rendered provider request | Separate cache table if responses get large |
| D3 | Intelligence artifacts | New generic table `artifacts` (kind, owner project/source, `version`, `status`, `data` JSONB validated by a Pydantic model per kind, `input_hash`, `approved_at`) + `artifact_dependencies`. Scripts/scenes keep `ScriptVersion`/`SceneVersion` | Typed tables per kind — more migrations, stronger DB constraints. Revisit if querying inside `data` becomes hot |
| D4 | Approval gates | Persisted as `approved_at` (+ approver) on `artifacts`, and on `script_versions` / `scene_versions` (which already own their versions), checked by workflow preconditions (`require_approved(kind)`). No new `ProjectStatus` explosion | Gate table (rejected: duplicates artifact state) |
| D5 | Source identity | `source_videos`: `url` nullable; new `kind` (`youtube`/`transcript`), `fingerprint` (sha256 of normalized transcript), `thumbnail_url`; uploads use `external_id = sha256`; unique `(platform, external_id)` kept | Per-channel canonical id from extractor output (KI-24) |
| D6 | Transcript storage | Raw file via `LocalStorage` (`raw_storage_key`), cleaned `text` + `segments` in DB, `normalizer_version`, `is_current`; version created by a service, never by the API payload | Store raw in DB (rejected: size) |
| D7 | Search v1 | Postgres full-text (generated `tsvector` + GIN) on `transcript_chunks.text`. No model needed | Semantic search is P11 |
| D8 | Embeddings | Deferred to P11. Before any embedding is written, add a startup/test guard that `Settings.embedding_dimensions == EMBEDDING_DIM` (KI-6) | A 768-dim local model fits the current column |
| D9 | Models | No model name hard-coded. Routine tasks (cleanup, tagging) → local small model if measured fast enough; creative stages (candidates, script) → strongest available provider via routing. **P2 includes a benchmark** of the user's actual options on this hardware | Free-tier cloud providers as the ₹0 path, behind routing |
| D10 | Images | `ImageGenerator` stays the interface; real adapter chosen after the P6 spike (local ComfyUI feasibility on CPU is unmeasured; a cloud/free-tier adapter or a deterministic vector-illustration fallback are options). Mock remains the default in tests | Decision pending until spike |
| D11 | Voice & audio | Require **WAV** output from `VoiceProvider` so duration is measured with the standard library (no ffprobe). Loudness/clipping checks in Python. Piper-class CPU TTS is an example to spike | Word-level alignment (whisper) is P12 |
| D12 | Render asset path | Timeline v2 carries project-relative asset keys; renderer is invoked with a per-project Remotion public dir and the composition resolves them via `staticFile`. Render runs as a subprocess with argument lists (no shell) in the runner | Local HTTP asset route (rejected for render; may be added for Studio preview) |
| D13 | Progress to UI | TanStack Query polling of `workflow_runs`; SSE later | |
| D14 | Auth | None; localhost only; bind `127.0.0.1` (KI-20) | P13 |
| D15 | CI | Add a minimal CI workflow (lint + tests with a pgvector service container) in P10, or earlier if cheap | Local-only checks (status quo) |

Open (not decided here): see [§10](#10-known-blockers-and-risks) and each phase file's "Decision points".

### Cross-file contracts (single owner each)

| Contract | Owner (defined in) | Consumers |
| --- | --- | --- |
| `workflow_runs` table, `GET /api/v1/runs/{id}` | P1 creates ([02](02-source-library.md)); P2 extends ([03](03-intelligence-runtime-and-understanding.md)) | P3–P9 |
| `llm_calls`, cache, routing, prompt registry, `artifacts` + `artifact_dependencies` | P2 ([03](03-intelligence-runtime-and-understanding.md)) | P3–P8 |
| Staleness semantics, `GET /projects/{id}/stages` | [versioning-and-invalidation.md](versioning-and-invalidation.md) | P9 ([07](07-studio.md)) |
| `GET /api/v1/assets/{id}/content` (file serving, resolves KI-17 for preview) | **P6-T9** ([05](05-visuals-and-audio.md)); P7 and P9 reuse it | P8 render uses staged files, not this route |
| Subtitle cues | P7 persists per-scene `Asset(type=subtitle)` JSON ([05](05-visuals-and-audio.md)) | P8 timeline assembly ([06](06-timeline-render-qa.md)) |
| Timeline v2, `timeline_hash`, render staging | P8 ([06](06-timeline-render-qa.md)) after the P0 spike ADR | P9 preview |
| Measured-duration policy | P7 ([05](05-visuals-and-audio.md)) | P8 |

**Hash vocabulary (do not mix):** `request_hash` = hash of one rendered provider request (`llm_calls`); `input_hash` = hash of the declared upstream *inputs* of an artifact/asset/script/scene version (staleness); `generation_key` = `input_hash` + prompt/provider/model/params/seed (cache and idempotency of AI generation); `timeline_hash` = hash of the canonical Timeline v2 including the asset manifest. Details: [versioning-and-invalidation.md](versioning-and-invalidation.md).

## 8. MVP definition

**Included:** one source (YouTube URL metadata + captions, or an uploaded TXT/SRT/VTT/pasted transcript) → stored and searchable (keyword) → AI source understanding → narrative opportunities → story candidates → **user picks one** → story architecture → script (10–15 min target, validated) → storyboard (scenes with shots, camera spec, image prompts) → user approves → Visual Bible/characters → one illustration per scene → TTS narration per scene with measured duration → deterministic subtitles → timeline v2 → Remotion render → MP4 → deterministic QA report; Studio exposing every stage with inspect/edit/approve/regenerate-one-scene and version history; cost/usage visible per project.

**Explicitly excluded (post-MVP):** channel scan/import/sync, embeddings/semantic search, multi-source projects, music/SFX and mixing/ducking, transitions beyond hard cuts, automated *visual* QA (model-based), word-level subtitle alignment, originality/similarity scoring, Temporal, MinIO, auth, cloud rendering, collaboration, deployment.

**Mocked/stubbed in tests (never claimed as real):** all LLMs (fake provider + recorded fixtures), image generation (mock PNG), TTS (generated WAV), yt-dlp (recorded `info` fixtures). **Real at least once, recorded in docs:** one end-to-end run with real providers on the dev machine.

**Local-only:** Postgres (Docker-free or Docker), filesystem storage, rendering, Remotion Studio preview. **Provider-dependent (user's choice via routing):** LLM, image, TTS.

## 9. Cross-cutting concerns

- **Migrations:** one Alembic revision per phase task group; review autogenerate output; run `upgrade → downgrade → upgrade` and `alembic check` in a test; keep the `CREATE EXTENSION` pattern.
- **Service layer:** introduce `app/<domain>/service.py` modules (NEW) for logic; routes stay thin; the generic CRUD factory remains for plain resources only.
- **Errors:** map `StoryWeaverError` subclasses to HTTP statuses (KI-8) via an exception handler before adding endpoints that raise them.
- **Observability:** every workflow/provider call logs `workflow_id`, `project_id`, `source_id`, `scene_id`, `provider`, `model`, `duration`, `status`, `error` (logging convention exists; KI-2 must be fixed first for token fields).
- **Schemas as contracts:** Pydantic models are the source of truth; `make schemas` exports JSON Schema; contract test pairs Python↔zod (KI-7) before Timeline v2.
- **Security:** validate URLs/paths with existing helpers; treat transcripts and model output as untrusted (prompt injection, schema validation); no shell with user input ([security docs](../docs/security/security-overview.md)).
- **Docs:** each phase's final task updates `status.md`, affected domain/workflow docs, and the changelog.

## 10. Known blockers and risks

| Risk | Impact | Mitigation in plan |
| --- | --- | --- |
| CPU-only machine: local LLM, image and TTS speed unmeasured | Schedule/feasibility of P3–P7 on ₹0 path | Measured spikes at P2/P6/P7 start; routing lets creative stages use a cloud/free-tier provider; fixtures keep CI/dev independent |
| Provider output quality/format variance | Invalid JSON, weak stories | Schema validation + repair retry; stage decomposition; recorded fixtures; prompts versioned and evaluated ([AI evaluation](../docs/testing/ai-evaluation.md)) |
| YouTube caption availability / yt-dlp breakage | P1 reliability | Manual transcript upload is first-class; extractor behind interface; recorded fixtures |
| Remotion render time/asset resolution | P8 | D12 spike in P0; fixture renders early |
| Image consistency across scenes | Product quality (P6) | Visual/Character Bible inputs recorded per asset; reference-image support deferred to P12 unless spike shows need |
| Scope creep into platform work | Delays MVP | §4 principle 4; post-MVP list is explicit |
| Docs/code drift | Misleading agents | Per-phase docs task; status.md is canonical |

## 11. Testing strategy

Uses the existing stack ([testing docs](../docs/testing/testing-strategy.md)); counts are not repeated here.

- **Unit:** pure functions (normalizers, fingerprinting, hashers, timeline builder, validators, staleness computation).
- **Database:** real Postgres + pgvector via `TEST_DATABASE_URL` (migrations run for real); each new table has constraint tests (uniqueness, FK, status).
- **API:** `TestClient` per endpoint incl. 404/409/422 and idempotent replays.
- **Provider contract tests:** a shared suite every `LLMProvider`/`ImageGenerator`/`VoiceProvider` adapter must pass using `httpx.MockTransport` (request shape, error wrapping per KI-3, timeouts). **No claim of live integration** unless a recorded manual run is documented.
- **Workflow tests:** fake provider + in-memory/ test DB; assert persisted state, idempotency (second run = no new calls), approval-gate blocking, retry after injected failure, restart reconciliation.
- **AI stage tests:** golden fixtures (recorded provider outputs) through the validator; prompt changes bump `prompt_version` and re-record.
- **Frontend:** Vitest for components/stores; Playwright for the stage flows against a seeded API with the fake provider (`PLAYWRIGHT_CHROMIUM_PATH` on this OS).
- **Media:** deterministic timeline JSON equality tests; render smoke test on fixtures asserting duration, resolution and a decoded frame; WAV measurement tests.
- **Failure injection (P10):** kill during job, provider timeout/garbage, missing asset, disk path errors.

## 12. Cost strategy in execution terms

Gate expensive work (P4 gate, P5 storyboard gate); cache every AI call by input hash (D2) and artifact by `input_hash` (so re-runs cost nothing); record tokens/cost estimate per call and show per-project totals (needs KI-2 fixed); route routine tasks to local/cheap models and creative stages to the strongest configured provider; never generate images/voice before the storyboard is approved; reuse one image across shots where the storyboard says so; no AI video generation. Details: [AI cost strategy](../docs/ai/ai-cost-strategy.md), [model routing](../docs/ai/model-routing.md).

## 13. Decision points still open

1. **D10 image backend** (after spike) and whether a deterministic vector-illustration fallback is worth building.
2. **D11 TTS engine** (after spike) and loudness standard (peak/RMS now; LUFS later).
3. **Which provider(s) serve creative stages** — configuration, not code; decided by the P2 benchmark.
4. **D15 CI timing/hosting.**
5. Whether `artifacts` (D3) should split into typed tables after P5 experience.
6. Per-stage prompt language/locale handling (English-only in MVP unless decided otherwise).

## 14. Definition of done (every phase)

1. All phase acceptance criteria pass, each backed by a test or a documented command.
2. `make lint` clean; `make test` green **with `TEST_DATABASE_URL` set** (DB tests actually ran); `make e2e` where UI changed; fixture render where media changed.
3. Migrations reviewed and tested up/down; `alembic check` clean.
4. No hard-coded provider/model; no AI-decided IDs/durations/paths.
5. Idempotency and failure paths tested; errors persisted on the entity.
6. `docs/reference/status.md`, affected docs and changelog updated; claims match the code.
7. Nothing committed or pushed unless the user asked.

## 15. Post-MVP roadmap (summary)

See [`08-hardening-and-post-mvp.md`](08-hardening-and-post-mvp.md): **P11** channel scan/import/sync, embeddings & semantic search, multi-source projects, collections/topics workflow; **P12** model-based visual QA, originality/similarity analysis, reference-image/LoRA consistency, transitions, music/SFX and mixing, word-level subtitle alignment; **P13** Temporal, MinIO, authentication, cloud rendering, deployment, collaboration.

## 16. Links

Design and status live in [`docs/`](../docs/README.md): [status](../docs/reference/status.md) · [architecture](../docs/architecture/overview.md) · [source library](../docs/domains/source-library.md) · [story generation](../docs/domains/story-generation.md) · [storyboard](../docs/domains/storyboard-system.md) · [workflow overview](../docs/workflows/workflow-overview.md) · [timeline spec](../docs/media/timeline-specification.md) · [Studio](../docs/frontend/studio.md) · [agent guide](../docs/development/ai-agent-guide.md).
