# P8 — Timeline, Render, Deterministic QA

> Execution plan for turning approved scenes plus their images, narration audio and subtitle cues into a validated Timeline v2, a rendered MP4, and a persisted deterministic QA report (Checkpoint H).

## Status

Planned. Master plan: [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) (phase **P8**, Checkpoint **H**, decisions **D1, D2, D3, D11, D12**). The *render itself* works today only as the manual `make render-sample`; everything below is **Planned — not implemented**. Design lives in [`docs/`](../docs/README.md) and is linked, not copied: [timeline specification](../docs/media/timeline-specification.md) · [Remotion](../docs/media/remotion.md) · [rendering](../docs/media/rendering.md) · [FFmpeg](../docs/media/ffmpeg.md) · [rendering architecture](../docs/architecture/rendering-architecture.md) · [render workflow](../docs/workflows/render-workflow.md) · [QA workflow](../docs/workflows/qa-workflow.md) · [QA domain](../docs/domains/quality-assurance.md) · [timeline domain](../docs/domains/timeline-system.md).

## 0. Baseline verified for this phase

Read from the working tree, not from documentation:

| Fact | Where |
| --- | --- |
| `Timeline` / `TimelineScene` v1: `scene_id: str`, `start`, `duration` (float seconds), `narration`, `subtitle` (one per scene), `image_src`, `audio_src` (raw strings), `camera: CameraSpec`; defaults `fps=30`, `1920×1080` | `apps/api/app/schemas/scene.py` |
| `build_timeline(scenes, fps)` sorts by `sequence`, `duration = s.duration or estimate_duration(narration)` (clamp 2–7 s, 2.5 words/s), accumulates **float** `cursor`, fills no `image_src`/`audio_src`, takes no DB or assets | `apps/api/app/video/timeline.py` |
| `renders` table: `project_id`, `status` (`queued/rendering/completed/failed`), `timeline` JSONB, `output_asset_id`, `started_at`, `finished_at`, `error`. `AssetType.RENDER` exists. No hash, progress, attempts, error code | `apps/api/app/models/domain.py`, `enums.py` |
| `/renders` is a **generic CRUD** resource whose `POST` takes only `project_id` and `PATCH` can set `status` freely | `apps/api/app/api/v1/router.py`, `schemas/resources.py` |
| `LocalRunner(max_workers=2)` + `WorkflowRunner` protocol; nothing submits jobs | `apps/api/app/workflows/runner.py` |
| `LocalStorage` (traversal-safe `path_for`, streaming `put`, sha256, size cap); no route uses it; no file-serving route ([KI-9](../docs/reference/status.md#known-issues-and-limitations), [KI-17](../docs/reference/status.md#known-issues-and-limitations)) | `apps/api/app/core/storage.py` |
| Remotion composition `Basic`: per-scene `Sequence` from `Math.round(start*fps)`; `<Img src={image_src}>` or dashed placeholder; `cameraTransform` (6 movements + static); one subtitle box per scene for the whole scene; optional `<Audio>`; no transitions; props schema = zod v1 (`camera` **required**, `shot` free string — differs from Python, [KI-7](../docs/reference/status.md#known-issues-and-limitations)) | `packages/video/src/{BasicComposition,camera,types,Root}.tsx/ts` |
| Render command: `remotion render src/entry.ts Basic out/sample.mp4 --props=./sample/timeline.json`; progress lines look like `Rendered 185/195, time remaining: 0s` then `Encoded 105/195` (observed in this repo) | `packages/video/package.json`, `Makefile` |
| `make schemas` exports `scene/timeline/normalized-source` JSON Schema; the zod mirror is hand-maintained | `scripts/export_schemas.py`, `packages/schemas/` |

### Verified constraint: the Remotion-bundled FFmpeg is a *reduced* build

Probed read-only (`ffmpeg -muxers/-encoders/-filters`, binaries under `node_modules/.pnpm/@remotion+compositor-linux-x64-gnu@4.0.530/…`). **This is the only FFmpeg the plan may rely on** (no system FFmpeg dependency).

| Needed for | Available in bundled ffmpeg n7.1 / ffprobe n7.1 | Not available (do not plan around) |
| --- | --- | --- |
| Container/stream probing | `ffprobe` (JSON output via `-print_format json`) | — |
| Frame sampling for QA/determinism | muxers `image2`, `image2pipe`, `null`, `wav`, `mp4`; encoders `png`, `mjpeg`, `libx264`; filters `scale`, `format`, `null` | muxers `rawvideo`, `framemd5`, `framehash`, `md5`; no raw-pixel pipe |
| Audio analysis | filters `silencedetect`, `loudnorm`, `volume`, `amix`, `aresample`, `atrim`; encoder `pcm_s16le`, muxer `wav` (decode final audio to WAV and analyse in Python) | `volumedetect`, `astats`, `ebur128` |
| Black/blank detection | — | `blackdetect`, `blackframe`, `signalstats`, `cropdetect` |

Consequence (drives the QA design below): frames are sampled as small grayscale **PNGs via `image2pipe`** and decoded in Python with a ~40-line stdlib PNG decoder; audio is decoded to **WAV via the `wav` muxer** and measured in Python; silence uses `silencedetect`. Task **P8-T1** re-verifies this on the machine that runs it before anything depends on it.

## 1. Task sequence (summary)

| Task | Title | Depends on | Section |
| --- | --- | --- | --- |
| P8-T1 | Binary location + capability spike (bundled ffmpeg/ffprobe) | — | [Storage/media](#storagemedia) |
| P8-T2 | Timeline v2 schema (Pydantic, zod, JSON Schema, contract fixtures) | P0-T6, P0-T7 | [Backend](#backend) |
| P8-T3 | Canonical JSON + `timeline_hash` | T2 | Backend |
| P8-T4 | `build_timeline_v2` (pure) + DB assembler | T2, T3, P5, P7 policy | Backend |
| P8-T5 | `validate_timeline` | T2 | Backend |
| P8-T6 | Remotion composition v2 | T2 | Backend |
| P8-T7 | **Fixture vertical slice** (mock image + generated WAV → MP4) | T3, T5, T6 | [Testing](#testing) |
| P8-T8 | Render migration, enum, router restriction, settings | T3 | [Database](#database) |
| P8-T9 | Storage additions (`adopt`) | — | Storage/media |
| P8-T10 | `render.project` workflow (stage → subprocess → finalize) | T4–T9, P2 runner | [Services/Workflows](#servicesworkflows) |
| P8-T11 | Render API (`/projects/{id}/renders`, `/renders/{id}/…`, timeline preview) | T8, T10 | [API](#api) |
| P8-T12 | QA module + `qa.run` + `qa_report` artifact + API | T1, T10 | Services/Workflows |
| P8-T13 | Render-time measurement (CPU-only) | T7 | Testing |
| P8-T14 | Determinism test | T7 | Testing |
| P8-T15 | Web: Render stage, QA panel, Player preview | T11, T12, P9 shell | [Frontend](#frontend) |
| P8-T16 | Docs, status, changelog | all | [Deliverables](#deliverables) |

Fixture-first rule: **T1–T7 can start as soon as P0-T6/T7 are done**, independent of P6/P7 content. T4's DB assembler and T15 wait for P5–P7 artifacts.

---

## Goal

A user (via API now, Studio at P9) can request a render of a project whose storyboard is approved and whose scenes each have a current image and measured-duration audio, and get back:

1. a **Timeline v2** that is a deterministic function of persisted inputs (same inputs ⇒ byte-identical canonical JSON ⇒ same `timeline_hash`);
2. a **validated** timeline (missing/stale assets, bad durations, gaps/overlaps, subtitle overflow reported *before* spending render time);
3. an **MP4** produced by Remotion from that timeline, tracked by a `Render` row with progress, errors, cancel and retry;
4. a **deterministic QA report** (`qa_report` artifact) with per-check pass/warn/fail attributed to scenes so the UI can offer "regenerate this scene's image/audio".

AI involvement in this phase: **none** (see [AI](#ai)).

## Why now

- It is the first point where every upstream artifact (script, scenes, images, audio, subtitles) must agree on one contract; building it against fixtures early (P8-T7) de-risks P6/P7 integration and fixes the `Timeline` contract that Studio preview (P9) also consumes.
- Rendering is the last expensive, deterministic step: it needs the P5 versioning/staleness model (to know which assets are *current*) and the P7 duration policy (measured audio, not estimates — [KI-16](../docs/reference/status.md#known-issues-and-limitations)).
- Checkpoint H (end-to-end MP4) is the first moment the product proves its core claim.

## Prerequisites

| Needed | From | Notes |
| --- | --- | --- |
| zod ↔ Pydantic contract test, `camera`/`shot` aligned | **P0-T6** ([KI-7](../docs/reference/status.md#known-issues-and-limitations)) | **Hard prerequisite of Timeline v2.** Do not edit `types.ts`/`scene.py` for v2 until it passes |
| Render asset-path spike + ADR + Timeline v2 field proposal | **P0-T7** (D12) | T2 consumes the proposal; if the ADR chose differently from D12, adapt T2/T6/T10 and record it under [Decision points](#decision-points) |
| Error mapping, config fixes, test isolation | P0-T1/T2/T5 | `StoryWeaverError` → HTTP before new routes raise them |
| Persisted runner (`workflow_runs`), `llm_calls`, `artifacts`, `artifact_dependencies` | **P2** (D1–D3) | `render.project`/`qa.run` are runner kinds; `qa_report` is an artifact kind |
| Approved storyboard, `SceneVersion` rows with shots, staleness computation | **P5** ([versioning-and-invalidation.md](versioning-and-invalidation.md)) | Defines "current scene version" and per-asset `input_hash` |
| Image assets per scene (current), `GET /assets/{id}/content` | P6 | If absent when T15 starts, P8 ensures the content route exists (single owner: whichever phase lands first — D-P9-2 in [07-studio.md](07-studio.md)) |
| WAV per scene with **measured** `duration_seconds`, subtitle cues, duration policy | P7 | Fixtures stand in until then |

---

## Backend

### Timeline v2 contract (P8-T2) — design

Code owns all timing. Integer **frames** are the source of truth (no float accumulation); seconds are derived and informational.

```jsonc
{
  "version": 2,
  "fps": 30, "width": 1920, "height": 1080,
  "duration_frames": 486,                       // == last scene start_frame + duration_frames
  "duration_source": "measured",                // "measured" | "estimated" (estimated is non-final)
  "assets": {                                   // manifest: every referenced key, content-addressed
    "images/3f2a….png": { "sha256": "…", "bytes": 482113, "mime": "image/png" },
    "audio/91bc….wav":  { "sha256": "…", "bytes": 1024044, "mime": "audio/wav" }
  },
  "scenes": [{
    "scene_id": "scene_001",                    // SceneSpec.scene_id (display key)
    "scene_row_id": "uuid",                     // scenes.id, for UI links; identifier mapping: docs/domains/storyboard-system.md
    "sequence": 1,
    "start_frame": 0, "duration_frames": 162,
    "shots": [{
      "shot_id": "scene_001/1",                 // deterministic: "<scene_id>/<n>"
      "start_frame": 0, "duration_frames": 162, // relative to scene start; shots tile the scene exactly
      "image_key": "images/3f2a….png",
      "crop": { "x": 0, "y": 0, "w": 1, "h": 1 }, // normalized 0..1, from the P5 shot plan; default full frame
      "camera": { "shot": "wide", "movement": "slow_zoom_in" }
    }],
    "audio": { "key": "audio/91bc….wav", "duration_frames": 154, "offset_frames": 0 },  // null when silent scene
    "subtitle_cues": [{ "start_frame": 0, "end_frame": 80, "text": "Long ago…" }]       // scene-relative
  }]
}
```

Rules (each enforced in T5 and covered by tests):

- **Durations:** `scene.duration_frames = ceil((audio_seconds + lead_in + tail) × fps)`; `lead_in`/`tail` are `RenderSettings` (defaults a small, configurable pad — values **Decision pending**, set by P7's duration policy; P8 consumes, does not invent). A scene without audio uses the P5 `SceneSpec.duration` only if `duration_source="estimated"`; **final renders refuse estimated timelines** (fixes the KI-16 misuse risk). Shots tile the scene; a single-shot scene is the MVP common case.
- **Asset keys** are project-relative, contain only `[A-Za-z0-9._/-]`, no `..`, and are derived from asset ids, never from user text. The manifest carries `sha256`/`bytes` from `Asset.checksum`/`size_bytes`, so `timeline_hash` pins asset *content*, not just ids.
- **Extensibility without breaking v2 consumers:** unknown optional fields under `scenes[].shots[]` and a top-level `transitions: []` (empty in MVP, **P12**) are reserved; a `version` bump is required for any semantic change. Transitions, music/SFX tracks and word-level cues are **not** in v2 MVP (hard cuts only).
- **Stored vs preview:** the stored/rendered timeline never contains URLs. The web layer may add an optional top-level `asset_urls: {key: url}` **only at the Player boundary** (matches [07-studio.md](07-studio.md)); `asset_urls` is excluded from the hash and rejected by the stored-timeline validator.
- **Backward compatibility:** the composition accepts v1 (the existing `sample/timeline.json`) and v2 through a zod union + `normalizeTimeline()` (v1 ⇒ v2 with one shot, frames = `round(seconds×fps)`); the Python v1 `Timeline` stays until P10, when v1 and `sample/timeline.json` are removed or migrated (decision recorded then).

### P8-T2 — Timeline v2 schema
- **NEW** `apps/api/app/schemas/timeline.py` — Pydantic `TimelineV2`, `TimelineSceneV2`, `ShotV2`, `CropRect` (validators: `0≤x`, `x+w≤1`, `w,h>0`), `AudioRef`, `SubtitleCue` (`end_frame>start_frame`), `AssetManifestEntry`, `RenderSettings` (fps, width, height, crf, lead_in, tail). `extra="forbid"` on stored models.
- **MODIFY** `apps/api/app/schemas/scene.py` — leave v1 `Timeline` untouched (compat).
- **MODIFY** `packages/video/src/types.ts` — zod `timelineV2Schema`, `timelineInputSchema = z.union([v1, v2])` discriminated by `version`, `normalizeTimeline()`; types exported from `index.ts`.
- **MODIFY** `scripts/export_schemas.py` — export `timeline-v2.schema.json` plus valid/invalid sample sets (extends P0-T6's mechanism).
- **MODIFY** `packages/video/src/contract.test.ts` (from P0-T6) — parse every v2 valid sample, reject invalid ones; Python test parses the same samples.
- **NEW** `packages/video/sample/timeline.v2.json` + fixture assets (`sample/public/images/…png`, `audio/…wav`) — produced by P0-T7's fixtures; reused here.
- **Acceptance:** adding/removing a field on one side only fails `make test`.

### P8-T3 — Canonical JSON and hash
- **NEW** `apps/api/app/video/hashing.py`: `canonical_json(model) -> str` = `json.dumps(model.model_dump(mode="json", exclude={"asset_urls"}), sort_keys=True, separators=(",", ":"), ensure_ascii=False)`; `timeline_hash(model) -> sha256 hex`. No floats in v2 except `crop` (rounded to 6 dp at construction) — everything else is integers/strings, so the hash is platform-stable.
- **Acceptance:** golden test: fixed input ⇒ fixed hash literal committed in the test; reordering input dict keys / scene list input order does not change the hash; changing any asset byte (manifest sha) changes it.

### P8-T4 — `build_timeline_v2` and assembler
- **MODIFY** `apps/api/app/video/timeline.py` — keep `estimate_duration`/`build_timeline` (v1) for compatibility; **add** pure `build_timeline_v2(inputs: TimelineInputs, settings: RenderSettings) -> TimelineV2`. No DB, no clock, no randomness, no filesystem; sorts by `sequence`; computes frames with integer arithmetic; derives shot ids; tiles shots; clamps nothing silently (invalid ⇒ `TimelineBuildError` with issue list).
- **NEW** `apps/api/app/video/assemble.py` — `assemble_inputs(db, project_id) -> TimelineInputs`: reads **current approved** `SceneVersion` per scene (P5), the current image `Asset` per shot and audio `Asset` per scene (selection = most recent `ready` asset whose recorded `input_hash` equals the current upstream hash — rule in [versioning-and-invalidation.md](versioning-and-invalidation.md)), subtitle cues (P7: one `Asset(type=subtitle)` JSON per scene, see [05-visuals-and-audio.md](05-visuals-and-audio.md)), and builds the manifest from `Asset.checksum/size_bytes/storage_key`. This is the **only** DB-touching part; everything downstream is pure.
- **Acceptance:** golden-file tests for 1-scene, 3-scene, shot-tiling, silent-scene and estimated cases; `build_timeline_v2` called twice with identical input returns equal objects and equal hashes; property test: for random durations, `sum(scene.duration_frames) == duration_frames` and scenes are contiguous with no gap/overlap.

### P8-T5 — `validate_timeline`
- **NEW** `apps/api/app/video/validate.py` — `validate_timeline(timeline, storage, *, allow_estimated=False) -> list[Issue]`, `Issue(code, severity: error|warn, scene_id|None, message, remediation: regenerate_image|regenerate_audio|rebuild_timeline|None)`.
- Checks (all deterministic): every `image_key`/`audio.key` exists in manifest **and** on disk (`LocalStorage.path_for` exists, size equals manifest `bytes`, sha256 equals manifest — hashing streamed, never reading whole files); image decodes (PNG/JPEG magic + dimensions via a small header reader; no new dependency); WAV decodes (`wave` stdlib: PCM 16-bit, rate/channels recorded; duration ≈ `audio.duration_frames` within 1 frame); `duration_frames > 0`; scenes contiguous and ordered; shots tile their scene; subtitle cues inside `[0, duration_frames]`, non-overlapping, `end>start`; crop rectangles valid; manifest has no unreferenced entries; `duration_source=="estimated"` ⇒ error unless `allow_estimated`; image aspect vs frame aspect mismatch ⇒ warn (cover-crop will occur); audio clipping on **source** WAVs (peak ≥ 0.999 FS or clipped-sample ratio above threshold) ⇒ warn with `regenerate_audio`.
- **Acceptance:** one test per check code (positive and negative); a timeline with a deleted file reports `asset_missing` with the right `scene_id`, and the render endpoint refuses (409) while any `error` issue exists.

### P8-T6 — Remotion composition v2
- **MODIFY** `packages/video/src/BasicComposition.tsx`: consume normalized v2; scene `Sequence from={start_frame} durationInFrames={duration_frames}` (integers, no `Math.round(seconds*fps)`); per shot a nested `Sequence`; `ShotView` renders `<Img src={resolve(image_key)}>` inside an `overflow:hidden` window; **crop** applied by a pure helper, then camera movement applied on a wrapper (order fixed and documented); per scene `<Audio src={resolve(audio.key)}>` inside the scene `Sequence` (starts at scene start + `offset_frames`); `<Subtitles>` shows the active cue.
- `resolve(key)` = `asset_urls?.[key] ?? staticFile(key)` (render: always `staticFile`; Player: URL map from the web layer).
- **NEW** `packages/video/src/crop.ts` — `cropTransform(rect) -> {scale, translateX, translateY}` pure; **NEW** `packages/video/src/Subtitles.tsx` + `subtitles.ts` — `activeCue(cues, frame)` pure; keep the existing dark rounded caption style (styling beyond that is P12).
- **MODIFY** `Root.tsx`: `schema=timelineInputSchema`; `calculateMetadata` uses `normalizeTimeline(props)` for `durationInFrames/fps/width/height`.
- **Failure behavior:** in the render path a missing/undecodable asset **fails the render** (Remotion `<Img>`/`<Audio>` raise) — the dashed placeholder remains only when `image_key` is `null` (Studio/dev). Validation (T5) is expected to catch it first.
- **Acceptance:** Vitest: `cropTransform` (identity, half-size, corner), `activeCue` boundaries (`end` exclusive), `normalizeTimeline(v1 sample)` equals expected v2, composition metadata for v1 and v2; `pnpm --filter @storyweaver/video typecheck` clean.
- **Do not** add transitions, music tracks, word-level highlighting or new fonts here (P12). Font determinism is tracked in P8-T14.

## Database

### P8-T8 — Migration (one revision: `render pipeline`)
Reuse `renders`; no new table for MVP QA (QA is an `artifacts` row, D3).

| Change | Detail |
| --- | --- |
| `renders.timeline_hash` `VARCHAR(64)` | add nullable → backfill existing rows with `sha256(canonical_json(timeline))` (rows can exist via the old generic POST with `timeline={}`) → set `NOT NULL`; index `(project_id, timeline_hash)` |
| partial unique index | `UNIQUE (project_id, timeline_hash) WHERE status IN ('queued','rendering','completed')` — makes `POST` idempotent by hash while **allowing** a new attempt after `failed`/`cancelled` (PostgreSQL partial index; `postgresql_where` in the model + migration) |
| `renders.progress` JSONB default `{}` | `{phase, frames_rendered, frames_encoded, frames_total, percent}` |
| `renders.attempts` `INTEGER NOT NULL DEFAULT 0` | incremented per run of the same row (retry) |
| `renders.error_code` `VARCHAR(32)` null | `validation`, `asset_missing`, `chrome_unavailable`, `timeout`, `oom`, `disk_full`, `render_failed`, `cancelled` |
| `renders.settings` JSONB default `{}` | resolved `RenderSettings` actually used (fps, size, crf, concurrency, remotion version) |
| `renders.log_tail` `TEXT` null | last ~4 KiB of renderer output on failure (secrets cannot appear: no provider keys are in the render env) |
| `renders.workflow_run_id` FK `workflow_runs.id` `ON DELETE SET NULL` | link to the P2 run (D1) |
| `RenderStatus` + `CANCELLED` | Python enum only — `status` is `VARCHAR(32)` with no CHECK, so no DDL needed |
| Index `(project_id, created_at DESC)` | list endpoint |

- **MODIFY** `apps/api/app/models/domain.py` (Render), `enums.py`, new `alembic/versions/<rev>_render_pipeline.py`; **MODIFY** `schemas/resources.py` (`RenderRead` gains `timeline_hash`, `progress`, `attempts`, `error_code`, `settings`, `qa` summary).
- **MODIFY** `apps/api/app/api/v1/router.py` — register `renders` with `create=None, update=None` (read + delete only); creation moves to the project-scoped route (T11). Removes the ability to `PATCH` a render to `completed` by hand.
- Data retention: deleting a `Render` deletes nothing on disk automatically; a P10 cleanup task removes orphaned `data/renders/**` and `data/projects/**/render/**` (not MVP-blocking, listed under Failure handling).
- **Acceptance:** migration upgrade → downgrade → upgrade → `alembic check` clean; DB tests: duplicate `(project, hash)` while `queued` ⇒ IntegrityError; same hash after `failed` ⇒ allowed; backfill test on a pre-existing row.

## API

All routes under `/api/v1`; no authentication (localhost, D14); errors via the P0-T5 handler; `limit/offset` conventions as in [API conventions](../docs/api/API-conventions.md).

| Method & path | Purpose | Request | Response / errors |
| --- | --- | --- | --- |
| `GET /projects/{id}/timeline` | Build (do not persist) the current timeline and validate it | query `mode=final\|preview` (default `final`), `allow_estimated=false` | `200 {timeline, timeline_hash, issues[]}`. `404` project; `409 {code:"timeline_not_buildable", issues[]}` when upstream is missing (no approved storyboard / no scenes). In `preview` mode, missing assets become `warn` and `image_key` may be `null` (placeholder) so Studio can show progress; `final` never does |
| `POST /projects/{id}/renders` | Request a render (**idempotent by `timeline_hash`**) | `{allow_estimated?: false, settings?: {fps?, width?, height?, crf?}}` — bounds-validated (e.g. fps 24–60, even width/height ≤ 3840×2160) | `201` new `Render` (`queued`) + `Location`; `200` existing `Render` for the same `(project, hash)` in `queued/rendering/completed`; `409` blocking validation `error` issues (body lists them); `422` bad settings; `507`-style disk guard ⇒ `409 {code:"disk_space"}` |
| `GET /projects/{id}/renders` | List renders, newest first | `limit,offset` | `200 [RenderRead]` |
| `GET /renders/{id}` | Detail incl. progress, error, QA summary | — | `200`, `404` (crud, read-only) |
| `POST /renders/{id}/retry` | Re-run a `failed`/`cancelled` render from its stored snapshot | — | `202`; `409` if status not retryable; increments `attempts`; refuses if inputs went stale unless the stored timeline's assets still exist and match their manifest (otherwise `409 {code:"inputs_changed"}` — create a new render instead) |
| `POST /renders/{id}/cancel` | Cancel `queued`/`rendering` | — | `202`; `409` otherwise |
| `GET /renders/{id}/content` | Download/stream the MP4 | `download=1` ⇒ `Content-Disposition: attachment` | `200/206` (Starlette `FileResponse` supports `Range`); path comes **only** from the `RENDER` asset's `storage_key` via `LocalStorage.path_for`, never user input; `404` if not `completed` |
| `GET /projects/{id}/qa` | Latest QA report for the project's latest completed render | — | `200 {render_id, timeline_hash, summary, checks[]}`, `404` if none |
| `GET /renders/{id}/qa` / `POST /renders/{id}/qa` | Read / (re)run QA for that render | POST: — | `GET 200/404`; `POST 202` (idempotent: unchanged inputs ⇒ cache hit, returns existing report) |
| `GET /runs/{id}` | Poll the underlying run (**P2**, not built here) | — | used by the UI for status |

- **NEW** `apps/api/app/api/v1/render.py` (router), **MODIFY** `router.py` to include it; schemas **NEW** in `schemas/render.py` (`RenderRequest`, `TimelineResponse`, `Issue`, `QaReport`).
- Idempotency, concurrency and replays: two simultaneous identical `POST`s ⇒ exactly one row (guaranteed by the partial unique index; the loser catches `IntegrityError` and returns the winner with `200`).
- **Acceptance:** API tests (render subprocess mocked): create → 201; repeat → 200 same id; changed asset sha ⇒ new hash ⇒ new 201; validation error ⇒ 409 with `scene_id`; retry only from `failed`; content route returns bytes with `Range`, rejects non-completed, never accepts a path; OpenAPI lists all routes.

## Frontend

(Minimal Render/QA stage views; the unified 10-stage shell, version history and dependency badges are [P9 / 07-studio.md](07-studio.md).)

### P8-T15 — Render stage, QA panel, Player preview
- **NEW** `apps/web/src/components/render/RenderPanel.tsx` — `Render` button (calls `POST …/renders`, shows validation issues from a 409 grouped per scene with a "Fix" link: `regenerate_image|regenerate_audio` → the P6/P7 per-scene action), list of renders with status badges, progress bar from `Render.progress` (TanStack Query polling `GET /renders/{id}` every 1–2 s while `queued/rendering`, stop on terminal), error + `error_code` text, Cancel/Retry, Download link (`/renders/{id}/content?download=1`), inline `<video controls src="/renders/{id}/content">` when completed.
- **NEW** `apps/web/src/components/render/QaPanel.tsx` — summary counts (pass/warn/fail), table of checks with severity badge, measured vs expected, scene link; "Re-run QA".
- **NEW** `apps/web/src/components/render/TimelinePreview.tsx` — `GET …/timeline?mode=preview`, then `<Player>` with the timeline plus `asset_urls` built **client-side** from `GET /assets/{id}/content` URLs (never stored; matches the P9 rule). Shows `duration_source` and warns visibly when `estimated`.
- **MODIFY** `apps/web/src/lib/api.ts` — types for `Render`, `Issue`, `QaReport`, `TimelineResponse`; parse FastAPI `detail` into `ApiError.detail` (currently ignored) so 409 issue lists render.
- **MODIFY** `apps/web/src/app/projects/[id]/page.tsx` (or the P9 stage page when it exists) to mount the panels; **state:** server state only via TanStack Query (keys `["render", id]`, `["renders", projectId]`, `["qa", renderId]`); Zustand untouched.
- States: loading skeletons, empty ("No renders yet"), error (`ErrorState`), cancelled/failed distinct, `aria-busy` while polling.
- **Tests:** Vitest — progress bar math, 409 issue grouping, status→badge mapping, polling stops on terminal state (fake timers); Playwright E2E against a seeded project with the **fake render** (see Testing) — request render, see progress reach completed, QA panel visible, download link present.
- **Acceptance:** a user can request, watch, cancel/retry, preview and download a render and see QA findings with scene links, with no console errors.

## Services/Workflows

### P8-T10 — `render.project` (runner kind; D1/D12)

Trigger `POST /projects/{id}/renders`. One `workflow_runs` row (`kind=render.project`, `subject=render_id`, `idempotency_key=f"{project_id}:{timeline_hash}"`). **Concurrency: 1** for this kind (a `threading.Semaphore`/kind limit in the P2 runner; if P2 did not provide per-kind limits, this task adds it) — a single 16 GB CPU machine cannot render two videos usefully.

Steps (each persists progress/state; each safe to re-run):

1. **Build + validate (deterministic).** `assemble_inputs → build_timeline_v2 → validate_timeline`; snapshot into `renders.timeline`, set `timeline_hash`. Any `error` issue ⇒ `failed`, `error_code=validation`, nothing staged. Disk guard: `shutil.disk_usage(storage_root).free ≥ RENDER_MIN_FREE_BYTES` (default a conservative 2 GiB — a guard, **not** a measurement; tuned by P8-T13).
2. **Stage inputs (immutable per render).** Create `data/projects/<project_id>/render/<render_id>/public/` and place each manifest asset at its key via hardlink (`os.link`, same filesystem) falling back to copy; verify sha256 after staging; write `timeline.json` (the exact canonical JSON) beside `public/`. Using a per-render dir means later regeneration of a scene can never alter an in-flight or past render's inputs.
3. **Render (subprocess, no shell).** `Popen([remotion_bin, "render", "src/entry.ts", "Basic", out_tmp, f"--props={timeline_json}", f"--public-dir={public_dir}", f"--concurrency={n}", "--overwrite", "--log=info"], cwd=REMOTION_PROJECT_DIR, stdout=PIPE, stderr=STDOUT, text=True, start_new_session=True, env=<allow-listed env: PATH, HOME, no provider keys>)` where `remotion_bin` is `packages/video/node_modules/.bin/remotion` (fallback `pnpm exec remotion`). Flags verified present in the installed CLI by P8-T1. `out_tmp = data/temporary/render-<render_id>/out.mp4`.
   - **Progress:** split output on `\r` and `\n`, regex `Rendered (\d+)/(\d+)` and `Encoded (\d+)/(\d+)` (format observed in this repo; pinned by a unit test with recorded lines — if Remotion changes it, the test fails loudly); write to `renders.progress` at most every 2 s.
   - **Timeout:** wall-clock `RENDER_TIMEOUT_SECONDS` (default 1800; tune after T13) ⇒ `killpg(SIGTERM)`, wait 10 s, `SIGKILL`; `error_code=timeout`.
   - **Cancel:** the run's cancel flag is polled between output lines; same kill sequence; `status=cancelled`; temp dir removed.
   - **Failure classification** from exit code/log: `Killed`/exit −9 ⇒ `oom`; Chrome download/launch failure text ⇒ `chrome_unavailable` (offline first run); `No space left` ⇒ `disk_full`; else `render_failed`; store `log_tail`.
4. **Finalize.** Probe the output (T12 helper); `LocalStorage.adopt("renders/<project_id>/<render_id>.mp4", out_tmp)` (T9: atomic move into storage, returns size+sha256); create `Asset(type=RENDER, status=ready, project_id, storage_key, mime=video/mp4, size, checksum, metadata={render_id, timeline_hash})`; set `Render.output_asset_id`, `status=completed`, `finished_at`; remove temp; keep `public/` for `RENDER_KEEP_STAGING_HOURS` (default 24) then cleanup in P10; set `Project.status=qa`; submit `qa.run`.
5. **Errors never touch the project:** a failed render leaves all scenes/assets/artifacts untouched; `Project.status` returns to its pre-render value.

### P8-T12 — QA module and `qa.run`
- **NEW** `apps/api/app/quality/` modules: `probe.py` (locate and run bundled `ffprobe` with an argument list, parse JSON), `frames.py` (`ffmpeg -ss <t> -i out.mp4 -frames:v 1 -vf scale=32:18,format=gray -f image2pipe -c:v png -` per sample time; **NEW** `png_gray.py` stdlib decoder for 8-bit grayscale non-interlaced PNG incl. filter types 0–4), `audio.py` (decode final audio `-vn -ac 1 -ar 44100 -c:a pcm_s16le -f wav -`, analyse samples with `array` — peak, clipped-sample count, per-window RMS), `checks.py` (pure functions → `Check`), `service.py` (`run_qa(db, render_id)`), `binaries.py` (**NEW**, `find_remotion_binary(name)`).
- **Locating the binaries (P8-T1):** `packages/video/scripts/where-binary.mjs` (NEW) resolves the platform compositor package from `@remotion/renderer`'s location (`createRequire`) and prints the absolute `ffmpeg`/`ffprobe` path; Python caches it; override `REMOTION_BINARIES_DIR`. This uses a Remotion-internal layout, so T1 verifies it and a test fails if resolution breaks after a Remotion upgrade.
- **Checks** (id → method → default severity → attribution):

| Check | Method | Severity | Scene attribution / remediation |
| --- | --- | --- | --- |
| `file.exists_nonzero` | stat | fail | — |
| `container.parse` | ffprobe JSON ok; `format_name` contains `mp4`; video stream `h264` | fail | — |
| `video.resolution_fps` | stream `width/height/r_frame_rate` == `timeline` | fail | — |
| `video.frame_count` | `nb_frames` (container) within ±1 of `timeline.duration_frames` | fail | — |
| `video.duration` | `abs(format.duration − duration_frames/fps) ≤ max(2/fps, QA_DURATION_TOLERANCE_SECONDS)` (default tolerance 0.1 s — **to be calibrated by T13/T14 data**) | fail | — |
| `audio.stream_present` | audio stream exists iff any scene has `audio` | fail | — |
| `audio.clipping` | on decoded output: peak ≥ 0.999 full scale or clipped samples > `QA_CLIP_MAX_SAMPLES` | warn | per scene window ⇒ `regenerate_audio` |
| `audio.silence` | `silencedetect=n=-50dB:d=1` (threshold **Decision pending**, calibrate on fixtures): every audio scene whose whole window is silent | fail | `regenerate_audio` |
| `video.blank_frame` | per scene sample at mid-point (and first/last frame): mean luma < 2 % or > 98 % **and** variance ≈ 0 ⇒ blank | warn (fail if *all* scenes blank) | `regenerate_image` |
| `video.freeze` (cheap) | adjacent scene mid-frames identical hash when images differ | warn | `rebuild_timeline` |
| `timeline.subtitle_bounds` | re-run T5 subtitle checks on the stored snapshot | fail | scene |
| `timeline.assets_current` | stored manifest vs current assets (stale since render?) | warn | marks the render *stale* (not failed) |

- **Artifact:** `artifacts(kind="qa_report", project_id, data={render_id, timeline_hash, qa_version, summary{pass,warn,fail}, checks[{id,status,severity,scene_id,scene_row_id,remediation,measured,expected,message}]}, input_hash=sha256(render_output_sha256 + timeline_hash + qa_version + settings))`, dependency edge → the render's output asset. Same inputs ⇒ same `input_hash` ⇒ `POST …/qa` returns the cached artifact (no rework). Project goes `qa → completed` when `fail == 0`; otherwise it stays `qa` and the UI lists failures with remediation links.
- **Acceptance:** fixture tests: a known-good fixture render ⇒ all pass; a deliberately corrupted variant per check (truncated file, wrong fps, silent audio, all-black image, clipped WAV) ⇒ the matching check fails/warns with the right `scene_id`; PNG decoder tested against files produced by the bundled ffmpeg and against hand-built filter-type cases.
- **Do not** add model-based visual QA, subjective scoring or loudness (LUFS) targets here (**P12**).

## AI

**None in P8.** Every step is deterministic code: timeline construction and hashing, validation, staging, subprocess control, probing, sampling and QA. No LLM or image/voice provider is called; no `llm_calls` rows are written. AI-produced inputs (scene text, image prompts, shot plans) arrive as already-persisted, validated artifacts. Responsibilities are therefore: **AI** — nothing; **deterministic** — IDs, frame/time arithmetic, asset references, hashing, validation, file management, rendering, QA, retries. Model-based visual QA is explicitly P12.

## Storage/media

- **Layout** (all under `STORAGE_ROOT`, i.e. `data/`; enforce [KI-1](../docs/reference/status.md#known-issues-and-limitations) fix first):
  - `data/projects/<project_id>/render/<render_id>/{timeline.json, public/images/*, public/audio/*}` — immutable staging per render.
  - `data/temporary/render-<render_id>/out.mp4` — in-flight output (deleted on failure/cancel).
  - `data/renders/<project_id>/<render_id>.mp4` — final output, referenced by an `Asset(type=RENDER)`.
- **P8-T9 Storage additions:** **MODIFY** `apps/api/app/core/storage.py` — `adopt(key, src_path) -> (size, sha256)` (atomic `replace` within the same filesystem, else stream-copy then delete; size cap applies; typed errors) and a typed `FileTooLargeError` replacing the bare `ValueError` ([KI-9](../docs/reference/status.md#known-issues-and-limitations)); `link_or_copy(key, dest)` helper for staging.
- **P8-T1 spike (do first, ~half a day):** on the dev machine record (a) the resolved ffmpeg/ffprobe paths, (b) `-muxers/-filters/-encoders` subset used in this plan (table above becomes a committed `docs/media/ffmpeg.md` note), (c) a 1-frame `image2pipe` grayscale PNG extraction and its decode, (d) `silencedetect` output parsing on a generated WAV, (e) that `remotion render` honours `--public-dir`, `--concurrency`, `--overwrite`, `--log`. Any miss changes the QA design **before** coding.
- **No system FFmpeg.** Remotion encodes (H.264/AAC in MP4 by default); no StoryWeaver code calls FFmpeg for *rendering*. FFmpeg's wider role (loudness, mixing, muxing extra tracks) stays **Decision pending** for P12 ([ffmpeg doc](../docs/media/ffmpeg.md)).
- **Serving:** `GET /renders/{id}/content` (API) and `GET /assets/{id}/content` (P6/P9) are the only file-serving routes; both resolve by database key through `LocalStorage` (traversal-safe, [file security](../docs/security/file-security.md)).
- **Resolutions are independent and must be explicit:** image generation size (P6), frame size (`RenderSettings`, default 1920×1080), and fixtures (1280×720). P8 does **not** resize assets; the composition uses `object-fit: cover` and T5 warns on aspect mismatch.

## Testing

Uses the existing stack; the render smoke tests are gated so default `make test` stays fast.

| Layer | NEW tests |
| --- | --- |
| Unit (pytest) | `test_timeline_v2.py` (golden JSON + hash literals, ordering invariance, frame arithmetic property tests, crop/cue validators); `test_timeline_validate.py` (one per check code); `test_render_command.py` (argument list exactly as specified, no shell, env allow-list, progress-line parser with recorded lines, failure classifier); `test_png_gray.py`; `test_qa_checks.py` (pure checks); `test_storage_adopt.py` (atomic move, traversal, size cap) |
| DB (pytest, real PG) | migration up/down/check; partial unique index semantics; backfill; `renders` read-only router (no create/patch) |
| API (pytest) | project timeline route (200/409/preview-vs-final); render create/idempotent/replay/retry/cancel/content-Range; QA routes; subprocess **mocked** with a fake `Popen` that emits recorded progress lines and writes a tiny fixture MP4 |
| Workflow | `render.project` end-to-end against the fake subprocess: state transitions, staging contents + sha verification, failure → `failed` + project untouched, cancel kills the process group (fake), restart reconciliation (`running → interrupted`, retry works), semaphore enforces concurrency 1 |
| Frontend (Vitest) | `crop.test.ts`, `subtitles.test.ts`, `normalizeTimeline.test.ts`, contract test (extends P0-T6), UI components (see Frontend) |
| Media (marked `@pytest.mark.render`, run by `make test-render`, **not** by `make test`) | **P8-T7 fixture vertical slice:** generate a mock PNG (`MockImageGenerator`) and a sine/silence WAV (stdlib `wave`), build a 3-scene Timeline v2, run the real `render.project` workflow with the real Remotion CLI, assert: MP4 exists, ffprobe resolution/fps/duration match the timeline within tolerance, audio stream present, a sampled frame is **not blank** and differs from a frame of another scene, QA report all-pass. **P8-T13:** record render wall-clock and peak RSS for a 60 s and a 5 min fixture at concurrency 1 and 2 on the CPU-only machine; publish numbers in `docs/media/rendering.md` as *measurements with the machine description*, then set `RENDER_CONCURRENCY`, timeout and disk-guard defaults from them. **P8-T14 determinism:** render the same fixture timeline twice and compare **decoded frames** (sampled PNG pixel hashes at fixed times, plus audio PCM hash), not container bytes |
| E2E (Playwright) | seeded project + fake render ⇒ progress → completed → QA visible → download link (uses the API with the render subprocess replaced by the test fake via a settings flag `RENDER_FAKE=1`, **forbidden outside tests**) |
| Contract | zod ↔ Pydantic v2 fixtures (extends P0-T6) |

### What determinism does and does not promise (P8-T14 decides the rest)

| Claim | Status |
| --- | --- |
| Same persisted inputs ⇒ identical canonical Timeline JSON and `timeline_hash` | **Guaranteed by construction; tested** (golden hashes) |
| Staged `public/` contents verified by sha256 against the manifest | **Guaranteed; tested** |
| Same timeline + assets + Remotion/Chrome versions on the same machine ⇒ identical decoded frames and audio PCM | **Expected, unverified until P8-T14**; if it fails, relax to a documented per-pixel tolerance and record why |
| Identical MP4 *file bytes* | **Not promised** (container timestamps, encoder threading, metadata) |
| Same frames across machines, OS, or Chrome versions; font rendering | **Not promised.** Fonts fall back to `sans-serif`; pinning a bundled open-licensed font is a **Decision point** for P8-T14 (license must be checked before adding a binary font file) |

## Observability

- Structured logs with `workflow_id`, `project_id`, `render_id`, `timeline_hash`, `phase`, `status`, `duration`, `error_code` for: build, validate, stage, render start/finish, probe, each QA check summary. Renderer output is **not** logged line-by-line (progress is throttled into `renders.progress`); only `log_tail` on failure. Note [KI-2](../docs/reference/status.md#known-issues-and-limitations) (P0-T3) must be fixed so frame/duration fields named like `*_tokens` are unaffected — avoid field names containing `key`, `token`, `secret`.
- Persisted per render: `started_at/finished_at` (wall-clock), `progress`, `settings` (incl. Remotion version and concurrency), `attempts`, `error_code`.
- Metrics are *derived* from DB rows (render duration vs video duration, failure rate by `error_code`); no metrics stack added.

## Failure handling & idempotency

| Failure | Behavior |
| --- | --- |
| Validation errors | Render not started; `409` lists issues with `scene_id` + remediation; project untouched |
| Missing/changed asset between validate and stage | Staging re-verifies sha256 ⇒ `failed`, `error_code=asset_missing`; user rebuilds (new hash) |
| Chrome unavailable (offline first run) | `chrome_unavailable`, `log_tail`; retry works once the browser is present |
| OOM / killed | `oom`; suggest lowering `RENDER_CONCURRENCY`; retry allowed |
| Timeout | process group killed; `timeout`; partial `out.mp4` and temp dir deleted |
| Disk full / low | pre-check `disk_space`; mid-render `disk_full`; temp removed |
| API restart mid-render | runner reconciles `running → interrupted` (P2); the `Render` is marked `failed` with `error_code=render_failed` + message "interrupted"; **retry** re-runs from the stored snapshot, restaging inputs |
| Cancel | process group killed, temp removed, `status=cancelled`, retryable |
| QA fails | render stays `completed` (file valid); `qa_report` shows failures; project remains in `qa` |
| Duplicate requests | one row per `(project, timeline_hash)` among active/completed renders |

Idempotency key table entry (canonical home: [retry-and-recovery](../docs/workflows/retry-and-recovery.md#idempotency-keys)): `render.project` = `(project_id, timeline_hash)` where the hash already covers asset content, settings and Remotion composition id; `qa.run` = `(render_output_sha256, timeline_hash, qa_version)`.

Staleness: a completed render is **stale** when `timeline_hash` of a freshly built timeline differs from `renders.timeline_hash` (computed on read per [versioning-and-invalidation.md](versioning-and-invalidation.md); never stored as a flag). A stale render is still downloadable.

Cleanup (P10, listed here for completeness): orphaned `data/renders/**`, expired `public/` staging dirs, `data/temporary/render-*` older than a threshold.

## Acceptance criteria

Checkpoint **H** — every item testable:

1. `make lint` clean; `make test` green **with `TEST_DATABASE_URL` set**; `make test-render` green on the dev machine.
2. `build_timeline_v2` is pure and deterministic: golden hashes pass; same inputs twice ⇒ identical JSON.
3. For a seeded project (approved storyboard, mock images, generated WAVs): `GET /projects/{id}/timeline` returns a valid Timeline v2 whose scene durations equal `ceil((measured audio + lead_in + tail) × fps)` and `duration_source="measured"`.
4. `POST /projects/{id}/renders` ⇒ MP4 under `data/renders/<project>/<render>.mp4`; `GET …/content` streams it with `Range`; `Asset(type=RENDER)` and `Render.output_asset_id` set; `progress` reaches 100 %.
5. Re-posting with unchanged inputs returns the same render (`200`); changing one asset ⇒ new hash ⇒ new render.
6. Final render of an `estimated` timeline is refused; preview is allowed.
7. QA: a good fixture render passes all checks; each injected defect (missing file, wrong fps, silent audio, all-black image, clipped WAV) is detected and attributed to the right `scene_id`.
8. Failure injection: killed subprocess, timeout, missing asset, low disk each end in the documented state with the project and other artifacts untouched, and retry succeeds after the cause is removed.
9. Cancel stops the Remotion process group (no orphan Chrome/node processes remain — checked in the media test).
10. No system FFmpeg required: the media test passes on a machine where `ffmpeg` is not on `PATH` (verified by running with a scrubbed `PATH` that still includes `node`/`pnpm`).
11. Determinism test (P8-T14) executed and its outcome recorded in `docs/media/rendering.md` (pass/relaxed-with-reason).
12. Render-time numbers (P8-T13) recorded with machine description; defaults updated from them.
13. UI: request, observe, cancel/retry, preview, download, QA-with-scene-links all work; Playwright passes.
14. `docs/reference/status.md` updated; KI-7/KI-16/KI-17 marked closed with phase references.

## Deliverables

- **NEW:** `schemas/timeline.py`, `schemas/render.py`, `video/{hashing,assemble,validate,render}.py`, `video/workflows.py` (kinds `timeline.build`, `render.project`, `qa.run`), `quality/{binaries,probe,frames,png_gray,audio,checks,service}.py`, `api/v1/render.py`, one Alembic revision, `packages/video/src/{crop,Subtitles,subtitles}.ts(x)`, `packages/video/scripts/where-binary.mjs`, `packages/video/sample/timeline.v2.json` (+fixtures from P0-T7), `apps/web/src/components/render/*`, tests listed above, `make test-render` target.
- **MODIFY:** `video/timeline.py`, `models/domain.py` (Render), `models/enums.py`, `core/storage.py`, `core/config.py` (+ `REMOTION_PROJECT_DIR`, `RENDER_CONCURRENCY`, `RENDER_TIMEOUT_SECONDS`, `RENDER_MIN_FREE_BYTES`, `RENDER_KEEP_STAGING_HOURS`, `REMOTION_BINARIES_DIR`, `QA_DURATION_TOLERANCE_SECONDS`, `QA_CLIP_MAX_SAMPLES`, `RENDER_FAKE` test-only), `api/v1/router.py`, `schemas/resources.py`, `packages/video/src/{types,BasicComposition,Root,index}.ts(x)`, `scripts/export_schemas.py`, `apps/web/src/lib/api.ts`, project/stage page, `Makefile`.
- **Docs to update (last task, P8-T16):** `docs/reference/status.md` (timeline, render, QA rows; close KI-7/16/17; add new KIs found), `docs/media/{timeline-specification,remotion,rendering,ffmpeg}.md` (v2, reduced-ffmpeg capability table, measurements, determinism outcome), `docs/workflows/{render-workflow,qa-workflow}.md`, `docs/api/` (new routes), `docs/data/` (renders columns), `docs/reference/environment-reference.md` (new settings), `docs/reference/changelog.md`.

## Dependencies

- **Upstream:** P0 (T6, T7, T1, T2, T5), P2 (runner/artifacts), P5 (approved scenes, staleness), P6 (image assets, content route), P7 (measured audio, cues). Fixtures allow T1–T7 to proceed without P6/P7 content.
- **Downstream:** **P9** (Studio) consumes the timeline preview endpoint, render/QA routes and `remediation` links; **P10** hardening consumes cleanup, failure-injection and render-time data; **P12** extends Timeline v2 (transitions, music/SFX tracks, word cues), model-based QA and loudness.

---

## Decision points

| ID | Question | Recommended | Needed by |
| --- | --- | --- | --- |
| D-P8-1 | Remotion CLI subprocess vs a Node script using `@remotion/renderer` | **CLI** (already verified working here; progress format is observable); switch to the API only if progress parsing proves brittle (adds direct deps `@remotion/renderer`, `@remotion/bundler`) | T10 |
| D-P8-2 | Lead-in/tail padding and any minimum scene length | Owned by P7's duration policy; P8 only consumes `RenderSettings` | T4 |
| D-P8-3 | Silence/blank thresholds and duration tolerance | Start with the values above; calibrate from T13/T14/fixture data; record in `docs/` | T12 |
| D-P8-4 | Pin a bundled font for determinism | Only after license check; otherwise accept per-machine font variance and document | T14 |
| D-P8-5 | Keep v1 `Timeline` after P10 | Remove v1 and migrate `sample/timeline.json` once nothing reads v1 | P10 |
| D-P8-6 | `POST /renders/{id}/retry` for stale inputs | Refuse (`409 inputs_changed`) rather than silently re-render different content | T11 |
| D-P8-7 | Who owns `GET /assets/{id}/content` | First phase to need it (P6 or P9); P8 only verifies it exists | T15 |

Disagreements with the master plan: none blocking. D12 is followed as written (project-relative keys + per-render Remotion public dir + `staticFile`; subprocess with argument list inside the runner), pending the P0-T7 ADR. One refinement: the staged public dir is **per render** (immutable inputs) rather than per project.

## Do NOT

- Do not call any LLM/image/voice provider from P8 code, and do not let any model output set durations, frame counts, ids, paths or statuses.
- Do not depend on a system `ffmpeg`/`ffprobe`; do not use filters/muxers outside the verified bundled set (`blackdetect`, `volumedetect`, `rawvideo`, `framemd5` are **absent**).
- Do not build shell command strings; do not pass user-controlled text into argv; never take file paths from request input.
- Do not store URLs in stored timelines; do not hash `asset_urls`.
- Do not use floats for timing in Timeline v2 (frames are integers).
- Do not run two renders concurrently, and do not delete project data on render failure.
- Do not claim determinism, performance or Chrome-offline behavior beyond what P8-T13/T14/T1 measured and recorded.
- Do not add transitions, music/SFX/ducking/LUFS, word-level subtitle alignment, model-based QA, cloud rendering or Temporal (P12/P13).
- Do not change application behavior outside this phase's files; inspect the code before each task and keep `v1` readable until P10.
