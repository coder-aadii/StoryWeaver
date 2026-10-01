# P6 Visuals and P7 Voice, Audio, Subtitles

> Execution plan for the first two *expensive* stages: one illustration per approved scene (P6) and one narration per scene with measured duration and deterministic subtitles (P7).

## Status

Planned. Current state, verified in the code (see [master plan §3](IMPLEMENTATION_PLAN.md#3-current-baseline-verified-against-the-repository)):

- **Visual:** `apps/api/app/visual/base.py` has the `ImageGenerator` ABC, `MockImageGenerator` (a 64×36 solid PNG, labelled mock) and `ComfyUIProvider` whose `generate()` **raises `ProviderError("… not implemented yet")`**. `get_image_generator()` returns the stub whenever `COMFYUI_BASE_URL` is set (**KI-18**). `ImageRequest` already carries `prompt`, `negative_prompt`, `width=1344`, `height=768`, `seed`, `reference_asset_ids`.
- **Voice:** `apps/api/app/voice/base.py` has `VoiceProvider`, `VoiceResult(data, mime_type, duration_seconds)` and `UnconfiguredVoiceProvider` (raises). No engine, no audio code.
- **Data:** `Asset` has `project_id`, `scene_id`, `type`, `status`, `storage_key`, `mime_type`, `size_bytes`, `checksum`, `error`, `meta` — **no `version`, `is_current`, `input_hash`, `scene_version_id`**. `Character` and `Location` tables exist (`name`, `description`, `attributes` JSONB, unique per project) with **no routes**. `CharacterVersion` is deferred.
- **Media:** `build_timeline` uses `SceneSpec.duration` or `estimate_duration` (2–7 s clamp, **KI-16**); `TimelineScene` has one `image_src`/`audio_src`; `BasicComposition` renders `<Img src>` directly (no `staticFile`, **KI-17**). `LocalStorage` exists but **no route uses it (KI-9)**; no route serves files. Pillow and numpy are **not** installed in `apps/api`.
- **Feasibility on the dev machine** (CPU-only Ryzen 5 5500U, 16 GB): local image generation and TTS speed are **unmeasured**. Each phase therefore starts with a spike whose *method and decision criteria* are defined here; **no result is claimed**.

Contract this file follows: [master plan](IMPLEMENTATION_PLAN.md) (phase ids, checkpoints F and G, decisions D3, D4, D10, D11, D12), [versioning and invalidation](versioning-and-invalidation.md) (artifact kinds, `require_approved`, `input_hash` staleness). Design lives in [visual system](../docs/domains/visual-system.md), [image generation](../docs/domains/image-generation.md), [character system](../docs/domains/character-system.md), [voice and audio](../docs/domains/voice-and-audio.md), [subtitle system](../docs/domains/subtitle-system.md), [consistency strategy](../docs/ai/consistency-strategy.md), [visual prompting](../docs/ai/visual-prompting.md), [asset data model](../docs/data/asset-data-model.md), [storyboard system](../docs/domains/storyboard-system.md#separate-concepts-intent--prompt--asset--shot).

## Shared rules for P6 and P7

**AI decides content; code decides execution.**

| | AI (via the P2 runtime) | Deterministic code |
| --- | --- | --- |
| P6 | Draft the Visual Bible and Character/Location attributes from the approved story/storyboard. (Scene-level `image_prompt` text was already drafted in P5.) | Prompt compilation, seeds, hashes, sizes, file paths, versions, `is_current`, statuses, retries, storage, validation, regeneration scope |
| P7 | *Nothing.* Narration text was written in P5. | Speech-text normalization, synthesis call, WAV parsing, **duration measurement**, trim/pad/normalize, clipping detection, scene-duration resolution, subtitle splitting and timing, versions, statuses |

**Scene / shot / asset separation** (do not blur; definitions in [storyboard system](../docs/domains/storyboard-system.md#separate-concepts-intent--prompt--asset--shot)): *scene intent* → *image prompt* (compiled deterministically in P6) → *generated asset* (`Asset` row, versioned) → *timeline shot* (P8). One image asset may serve several shots; shot reframing (crop/zoom/pan) is **timeline data, not extra generation**.

**Gate:** both phases require `require_approved('storyboard')` (D4) before any provider call; endpoints return `409` otherwise. Mock providers never need the gate to be bypassed in tests — tests approve a fixture storyboard.

**Dependencies on other plan files (assumptions to verify at execution):** P2 provides `workflow_runs`, the job helper, provider-error wrapping (KI-3) and `llm_calls`; P4/P5 provide the `artifacts` table and generic artifact endpoints, `Scene`/`SceneVersion` data with `SceneSpec.image_prompt`, `negative_prompt`, `characters`, `locations`, `camera`, and (decision in P5) a `shots` list. If P5 did **not** add `shots`, P6/P7 treat every scene as one shot — nothing here depends on multiple shots existing.

**Known issues assigned here:** KI-18 (P6-T6), KI-9 (P6-T3), KI-17 (P6-T9 + P8), KI-16 (P7-T5), KI-8 (error mapping from P0 must exist), KI-4 (nested settings validated by dedicated endpoints, P7-T7).

---

# Phase P6 — Visuals (Checkpoint F)

## Goal

Every approved scene has a stored, versioned illustration produced from a deterministic, hash-recorded prompt; a Visual Bible and Character/Location definitions keep the look consistent; one scene can be regenerated without touching any other; the browser can display the files.

## Why now

Images are the most expensive generation step and are meaningless before the storyboard is approved (P5). They are independent of audio (P7), so P6 and P7 can run in parallel. The asset-versioning migration and the file-serving route built here are reused by P7 and P8.

## Prerequisites

P0 (KI-8 handler, KI-9 groundwork, D12 spike result), P2 (runs, provider wrapping, `llm_calls`), P5 (approved storyboard, `Scene`/`SceneVersion` content, `artifacts` + approval). Checkpoint E passed.

## Backend

Files are *likely* locations; inspect `apps/api/app/visual/` and follow its naming. `NEW` = does not exist now.

| Task | Work | Files |
| --- | --- | --- |
| **P6-T1 Spike S6 — image backend (decision D10)** | Define and run the harness; record results in a decision record (ADR, NEW `docs/decisions/ADR-0xx-image-backend.md`, number at execution). **Not an implementation task.** | NEW `scripts/spikes/image_backend_spike.py` (location undecided; `scripts/` holds `dev_postgres.py`, `export_schemas.py` today) |
| **P6-T2 Asset versioning migration** | Add versioning columns to `assets` (see Database) | MODIFY `models/domain.py`, `models/enums.py` (if needed); NEW Alembic revision |
| **P6-T3 Asset service + storage wiring (KI-9)** | Create/store/version/set-current assets through `LocalStorage` | NEW `visual/assets.py` (or `visual/service.py` — match the service naming P1 chose); MODIFY `core/storage.py` only if a typed size-limit error is needed (it raises plain `ValueError` today) |
| **P6-T4 Bible schemas, presets, Character/Location attributes** | Pydantic models + deterministic style presets | NEW `schemas/visual.py`, NEW `visual/presets.py` |
| **P6-T5 `visual_bible.generate` workflow** | AI-drafts the Visual Bible and character/location attributes into an artifact | NEW `visual/bible.py`; prompt NEW under `packages/prompts/visual_bible/v1.md` (follows the P2 prompt-registry layout) |
| **P6-T6 Prompt compiler + provider selection (KI-18)** | Pure compiler; explicit `IMAGE_PROVIDER` setting | NEW `visual/prompt_compiler.py`; MODIFY `visual/base.py` (`get_image_generator`), `core/config.py`, `.env.example` |
| **P6-T7 Real image adapter(s)** | ComfyUI client and/or the adapter the spike selects | NEW `visual/comfyui.py` (keeps `base.py` as ABC + mock); optional NEW `visual/<chosen>.py` |
| **P6-T8 `scene.image` workflow** | Per-scene idempotent generation; project-wide run | NEW `visual/workflows.py` |
| **P6-T9 File-serving route + image header validation (KI-17)** | `GET /api/v1/assets/{id}/content`; stdlib PNG/JPEG header parse | NEW `api/v1/assets_content.py`, NEW `visual/imageinfo.py` |
| **P6-T10 Characters/Locations/Visual routes** | Project-scoped CRUD, generate, regenerate, set-current | NEW `api/v1/visual.py`; MODIFY `api/v1/router.py` |
| **P6-T11 Frontend Visuals stage** | Grid, bible editor, compare, regenerate | NEW `apps/web/src/app/projects/[id]/visuals/page.tsx` + components |
| **P6-T12 Tests and fixtures** | See Testing | `apps/api/tests/…`, `apps/web/…` |
| **P6-T13 Docs + status** | See Deliverables | `docs/…` |
| P6-T14 *(conditional)* Reference-image upload | Only if the spike shows reference conditioning is needed in MVP | see API |

### P6-T1 Spike S6 — method

Candidates (examples, not commitments): **(a)** local ComfyUI with a Stable-Diffusion-class checkpoint on CPU; **(b)** the same ComfyUI on a GPU machine if the user has access to one; **(c)** a free-tier/low-cost cloud image API behind a new `ImageGenerator` adapter; **(d)** a deterministic, code-drawn vector-illustration route (structured intent → SVG, rendered by Remotion) as a fallback when (a)–(c) fail the criteria — (d) is a *different visual product* and needs an explicit product decision before any work.

Measure, per candidate, on 10 fixed prompts of varying complexity at the project's target resolution (default `ImageRequest` is 1344×768): **seconds per image** (cold and warm), **peak RAM** (the machine has 16 GB shared with Postgres, Node and the browser), **failure/timeout rate**, **determinism** (same seed + same inputs → identical bytes? identical enough?), and a **manual style-adherence rubric** (e.g. 0–2 per prompt for style, subject, no artifacts). Download model files **manually**, never automatically.

Decision arithmetic to write into the decision record (inputs are the user's, not assumed): `images_needed ≈ video_seconds / (avg_shot_seconds × shots_per_image)`. Example only: 600 s ÷ (6 s × 2) ≈ 50 images. `total_generation_time = images_needed × seconds_per_image`. The user sets the acceptable total (e.g. "overnight"); candidates exceeding it are rejected. Output: chosen adapter(s), default resolution, concurrency limit, and whether (d) is pursued.

### P6-T6 Prompt compiler — specification

Pure function, no I/O, no model:

```text
compile_image_request(scene_version: SceneSpec, bible: VisualBible, characters: list[CharacterAttrs],
                      locations: list[LocationAttrs], *, seed_salt: int, provider: str, model: str)
  -> CompiledImagePrompt{prompt, negative_prompt, width, height, seed, input_hash, compiler_version}
```

- Prompt = ordered fragments: subject/action from `SceneSpec.image_prompt` (the P5 intent-level text) → character fragments (looked up by `SceneSpec.characters` names, case-insensitive; **unknown name = validation error, never silently dropped**) → location fragment → bible style fragments (art style, illustration style, line quality, palette, lighting, composition rules). Fragment order and a priority-based trimming rule (when over the configured max prompt length) are fixed and documented in the module; `compiler_version` is a string constant bumped on any rule change.
- Negative prompt = `bible.negative_prompt_base` + `SceneSpec.negative_prompt`, de-duplicated preserving order.
- Size from `bible.aspect_ratio` (+ configured base resolution), not from `Timeline` defaults (the three resolutions — 1344×768 image default, 1280×720 sample, 1920×1080 timeline default — are unreconciled today; P8 resolves the render size; images are fit with `object-fit: cover`).
- Seed = first 32 bits of `sha256(project_id|scene_id|seed_salt)`. Regenerate-with-new-seed increments `seed_salt` (stored in `Asset.meta`). Same inputs ⇒ same seed.
- `input_hash` = `sha256(canonical JSON {prompt, negative_prompt, width, height, seed, provider, model, compiler_version, bible_hash, character_hashes, location_hashes})`. This is the staleness/idempotency key ([design](versioning-and-invalidation.md)).
- **CharacterVersion decision (left to the user, recommended default):** do **not** add `CharacterVersion` in MVP. Record `character_hashes` (sha256 of canonical attributes JSON) on each asset's `meta`/`input_hash`; "this image was made with an older definition" = hash mismatch. Revisit if users need to browse historical character definitions.

## Database

Reuse: `Asset`, `Character`, `Location`, `Scene`, `SceneVersion`, artifact kind `visual_bible` (D3), `workflow_runs`.

**Migration `assets_versioning` (P6-T2)** — *coordinate with P5: if [versioning-and-invalidation.md](versioning-and-invalidation.md) or P5 already added any of these columns, reuse them instead of re-adding.*

| Change | Detail |
| --- | --- |
| `assets.version` | `Integer NOT NULL`, server default `1` (table is empty today; no backfill) |
| `assets.is_current` | `Boolean NOT NULL` server default `false` |
| `assets.input_hash` | `String(64)` nullable, **indexed** (sha256 hex) |
| `assets.scene_version_id` | UUID FK → `scene_versions.id` `ON DELETE SET NULL`, nullable, indexed (which `SceneVersion` produced it) |
| unique | `(scene_id, type, version)` — only enforced when `scene_id IS NOT NULL` (PG treats NULLs as distinct, so a plain unique constraint is correct) |
| partial unique index | `ON assets (scene_id, type) WHERE is_current` — at most one current asset per scene and type |
| `assets.meta` keys (convention, no DDL) | `provider`, `model`, `seed`, `seed_salt`, `compiler_version`, `width`, `height`, `attempts`, `duration_ms`, `error_detail`; character/location/bible hashes |

Downgrade drops the index, constraint and columns. Tests: `upgrade → downgrade → upgrade`, `alembic check`, constraint behaviour (two currents rejected; duplicate version rejected).

Characters/Locations: **no schema change**. Define the `attributes` key sets in Pydantic (P6-T4) and validate on write:

- `CharacterAttributes`: `age`, `appearance`, `hair`, `skin_tone` (optional), `clothing`, `body_type`, `accessories[]`, `personality_cues[]`, `style_notes`, `reference_asset_ids[]`.
- `LocationAttributes`: `era`, `environment`, `lighting`, `palette[]`, `key_objects[]`, `style_notes`.

Unknown keys are rejected on API writes (existing rows with other keys, if any, are tolerated on read). Names remain the join key from `SceneSpec.characters` (a convention made explicit and enforced by the compiler).

`VisualBible` artifact (`artifacts.data`, validated by `schemas/visual.py`): `art_style`, `illustration_style`, `line_quality`, `palette[]` (hex), `lighting`, `environment_language`, `camera_language`, `aspect_ratio` (`"16:9"`), `composition_rules[]`, `reference_asset_ids[]`, `negative_prompt_base`, `consistency_rules[]`, `preset` (name or null). Edits create a new artifact version; approving sets `approved_at` (D4). `bible_hash` is the artifact's `input_hash`/content hash.

## API

All under `/api/v1`; no authentication (localhost, D14); errors via the KI-8 handler: `404` missing, `409` precondition/conflict, `422` validation.

| Endpoint | Purpose / concept | Validation & errors | Idempotency |
| --- | --- | --- | --- |
| `GET /projects/{id}/characters`, `POST /projects/{id}/characters` | List / create (body: `name`, `description`, `attributes`) | `CharacterAttributes`; `409` duplicate `(project_id, name)`; `404` project | n/a |
| `GET/PATCH/DELETE /characters/{id}` | Read / edit / delete | PATCH validates attributes; reject explicit `null` on `name` (KI-4: do not reuse the generic null behaviour); `409` if referenced by a non-stale asset? **No** — delete allowed, assets become stale by hash | — |
| same for `/projects/{id}/locations`, `/locations/{id}` | Locations | as above | — |
| `POST /projects/{id}/visual-bible/generate` | Start `visual_bible.generate` (`{preset?: string}`); with `preset` and no AI call, applies the preset deterministically | `409` if storyboard not approved; `422` unknown preset; returns `202 {run_id}` | key = `(project_id, story_architecture_hash, storyboard_version, preset, prompt_version, model)`; cache hit → run completes with 0 calls |
| Visual Bible read / edit / approve | **Use the generic artifact endpoints** defined with the `artifacts` table (see [versioning-and-invalidation.md](versioning-and-invalidation.md)); P6 adds no duplicate | — | — |
| `POST /projects/{id}/images` | Start `scene.image` for all scenes (`{scene_ids?: uuid[], force?: bool}`); `202 {run_id}` | `409` storyboard or Visual Bible not approved; `422` bad ids/scene not in project | per-scene key = `input_hash`; `force` creates a new seed salt |
| `POST /scenes/{id}/images` | Regenerate **one** scene (`{new_seed?: bool}`) | `409` preconditions; `404` | same |
| `GET /scenes/{id}/assets?type=image` | List versions (version, status, is_current, `input_hash`, meta subset, stale flag) | `404` | — |
| `POST /assets/{id}/set-current` | Make a ready version current (atomic flip) | `409` if asset not `ready` or not an image/voice for its own scene; `404` | repeat = no-op |
| `GET /assets/{id}/content` | Stream the file for preview/render (**KI-17**) | see below | read-only |
| *(P6-T14, conditional)* `POST /projects/{id}/assets/reference` | Upload a reference image (multipart) | max size (`MAX_UPLOAD_BYTES` and a smaller image cap), sniff magic bytes (PNG/JPEG only), **server-generated storage key**; the client filename is sanitized (`sanitize_filename`) and stored only as display metadata; `413` too large, `415` bad type | key = sha256 of bytes; duplicate upload returns the existing asset |

**`GET /assets/{id}/content` specification:** resolves the asset, requires `status == ready` and a `storage_key`, opens via `LocalStorage` (re-validated by `path_for`, so traversal is impossible even if a key were corrupted); `Content-Type` from a fixed allowlist (`image/png`, `image/jpeg`, `audio/wav`, `application/json`, `text/vtt`, `text/plain` for SRT) — anything else → `415`/`500` never reflected from user input; `X-Content-Type-Options: nosniff`; `Content-Disposition: inline`; `ETag` = stored sha256; `Cache-Control: private, max-age=…` (content is immutable per asset id/version). **Range requests:** needed for `<audio>` seeking; *verify at implementation whether the installed Starlette `FileResponse` supports `Range`* and if not implement single-range handling with a test. Streams in chunks; never loads a file into memory.

## Frontend

- **P6-T11 Visuals stage** — NEW route `apps/web/src/app/projects/[id]/visuals/page.tsx` (Studio P9 later embeds the same components; do not build a parallel layout).
  - **Bible panel:** preset picker + "Draft with AI" (starts the run) + editable form for the `VisualBible` fields + Approve. Character/Location lists with an attributes form.
  - **Scene grid:** per scene — thumbnail (`/assets/{id}/content`), state badge (`pending/generating/ready/failed/stale`), "Regenerate" (and "new seed"), version list with compare (side-by-side) and "Set current".
  - **Run progress:** TanStack Query polling of `GET /runs/{id}` (D13) with `refetchInterval` only while active; shows `done/total/failed`; failed scenes show the persisted error and a Retry.
  - Query keys: `['project', id, 'visual-bible']`, `['project', id, 'images']`, `['scene', sceneId, 'assets']`; invalidate on run completion. Zustand only for transient UI (selected compare pair); server state stays in TanStack Query.
- Reuse existing `StatusBadge`, `states.tsx` (`EmptyState/ErrorState/LoadingRows`), `ResourceList` patterns; add NEW small components (`SceneImageCard`, `VersionCompare`, `RunProgress` — if P2/P9 already created a run-progress component, reuse it).
- Empty/blocked states: "Approve the storyboard first" when the gate is closed.

## Services/Workflows

| Workflow kind | Trigger | Inputs | Outputs / persisted state | Retry & idempotency |
| --- | --- | --- | --- | --- |
| `visual_bible.generate` | API (above) | Approved story architecture + storyboard summary (+ preset) | `artifacts(kind=visual_bible)` draft version; `llm_calls` row | Cache by `input_hash`; retries per P2 policy |
| `scene.image` | API per scene / run | Current `SceneVersion`, approved `visual_bible`, referenced characters/locations | `Asset(type=image)` version N+1, then `is_current` flip | Key `input_hash`; existing ready asset with same hash ⇒ no provider call |
| `images.generate_all` (run) | API | list of scene ids (default all) | `workflow_runs.progress {done,total,failed}` | Sequential by default (`IMAGE_CONCURRENCY=1`); continues past failed scenes; ends with the P2 "completed with errors" outcome (name per [03-intelligence-runtime-and-understanding.md](03-intelligence-runtime-and-understanding.md)); re-running skips ready scenes |

**`scene.image` algorithm (P6-T8):** (1) assert gates; (2) load current `SceneVersion` + approved bible + referenced characters/locations; (3) compile (P6-T6) → `input_hash`; (4) if a `ready` asset with this `input_hash` exists for the scene: set current if needed, return — **zero provider calls**; (5) insert `Asset(status=generating, version=max+1, scene_version_id, input_hash)`; (6) call the generator with timeout; retry ≤ 2 times with backoff on transient `ProviderError`; **never** retry `ProviderNotConfiguredError` or validation errors; (7) validate bytes (`imageinfo`: PNG/JPEG signature + dimensions > 0 + sane size); (8) store via `LocalStorage.put` at `images/<project_id>/<scene_id>/v<N>.<ext>`, record size/sha256/mime; (9) in one transaction mark `ready` and flip `is_current` (previous current untouched on failure); (10) failure ⇒ `status=failed`, `error` persisted, previous current preserved.

**Shot reuse (planning only):** if `SceneVersion` declares *k* shots, `scene.image` still makes **one** asset; the timeline (P8) derives per-shot crop/zoom/pan from the shot specs. Test: scene with 3 shots ⇒ exactly 1 provider call.

## AI

- **Tasks:** `visual_bible` (one call per project, drafts Bible + character/location attributes). Routed by the P2 router; model ids from settings; no vendor hard-coded. Quality needs: structured JSON; strong enough instruction-following — local small models may suffice for drafting from a preset; use the benchmark from P2.
- **Prompt:** NEW `packages/prompts/visual_bible/v1.md`; `prompt_version` recorded on the artifact; output validated by `VisualBible` Pydantic; one repair retry per P2 policy; cache by input hash.
- **Not AI:** compiling image prompts, seeds, sizes, hashes (Principle 1).
- **Image models are not LLMs:** `ImageGenerator` stays separate from `LLMProvider`; no usage tokens — record `duration_ms`/`attempts` in `Asset.meta`.
- **Originality/consistency:** no claim that images are consistent; the plan records inputs so inconsistency can be diagnosed ([consistency strategy](../docs/ai/consistency-strategy.md)). Reference-image conditioning, LoRA and ControlNet are P12.

## Storage/media

- Keys: `images/<project_id>/<scene_id>/v<N>.png|jpg` (the `data/images/` bucket exists). Server-generated keys only; user filenames never used for keys.
- Expected size (typical, **unmeasured**): illustration PNGs are of the order of hundreds of KB to a few MB; ~50–100 images per video ⇒ tens to low hundreds of MB.
- Retention: old versions kept (cheap, enables compare/rollback); a cleanup command is P10. Failed attempts leave no file (write goes to `.part` then rename — already how `LocalStorage.put` works).
- No Pillow in MVP by default: images are stored as produced; fitting is done by `object-fit: cover` in the composition. **Decision point D-P6-1 (new dependency):** add Pillow for (a) decode-validation, (b) blank-image detection, (c) resizing/format normalization. Default: **no**; header validation only via `visual/imageinfo.py`; blank/artifact detection is P12. Revisit if the spike backend returns formats the stdlib parser cannot handle (e.g. WebP).

## Testing

Existing stack only; no live-provider claims.

- **Unit:** prompt compiler (golden outputs; fragment order; trimming; unknown character ⇒ error; seed/`input_hash` stable across runs and changes with each input); `imageinfo` on PNG/JPEG fixtures and truncated/garbage bytes; asset version/current logic.
- **DB:** migration up/down/check; partial unique index rejects two currents; unique `(scene_id,type,version)`; FK `SET NULL`.
- **Provider contract (httpx.MockTransport):** ComfyUI client — submit/poll/fetch/timeout/error-status mapping to `ProviderError`; assert no secrets in logs. **Fixtures are synthetic until recorded from a real ComfyUI during the spike; label them so.** Shared contract suite also runs against `MockImageGenerator`.
- **Workflow (fake generator):** idempotent re-run = 0 calls; changed Bible ⇒ new hash ⇒ new version; failure keeps previous current; one-scene regeneration leaves other scenes' assets untouched (assert row ids/versions unchanged); gate closed ⇒ `409`; restart reconciliation inherited from P2.
- **API:** every endpoint incl. `409/422/404`; `content` route: traversal attempt, wrong status, range (if implemented), headers.
- **Frontend:** Vitest for card states and compare/regenerate; Playwright (mock generator seeded API): approve bible → generate all → thumbnails → regenerate one → v2 → set current. (`PLAYWRIGHT_CHROMIUM_PATH` on this OS.)

## Observability

Structured logs on every attempt with `workflow_id`, `project_id`, `scene_id`, `provider`, `model`, `duration`, `status`, `error` (no prompts containing secrets; prompts are not secrets but are not logged at INFO by default — log hashes). Counters in `workflow_runs.progress`. Extend `GET /health/providers` with image provider selection, configured, reachable (fixes the KI-18 confusion: report *selected* provider, not just "configured"). KI-2 is irrelevant here (no token fields) but must be fixed by P2 for the shared logging.

## Failure handling & idempotency

Per-scene failure never fails the project. `ProviderNotConfiguredError` ⇒ run fails fast with an actionable message (no retries). Timeouts bounded by `IMAGE_TIMEOUT_SECONDS` (NEW setting) and a ComfyUI queue-wait cap. Interrupted run ⇒ `interrupted`; re-run resumes by skipping ready hashes. Partial `Asset(generating)` rows older than a threshold are reconciled to `failed` on startup. Disk-full/permission errors surface as `failed` with the OS error class (no path leakage in API responses). Content route never 500s on a missing file: returns `404`/`410` and marks nothing.

## Acceptance criteria (Checkpoint F)

1. `make lint`, `make test` (with `TEST_DATABASE_URL`), `make e2e` green; migration up/down/up and `alembic check` clean.
2. With `IMAGE_PROVIDER=mock`, a fixture project with an approved storyboard and Bible produces one `ready`, `is_current` image per scene; re-running the run makes **0** generator calls.
3. Changing one scene's `SceneVersion` then regenerating that scene creates version 2 for **that scene only**; other scenes' asset ids/versions are unchanged (test-asserted).
4. Changing the Visual Bible makes every scene's image report `stale` (hash mismatch) without regenerating anything.
5. A failed generation leaves the previous current image current and persists the error; Retry succeeds.
6. `GET /assets/{id}/content` returns the exact stored bytes with correct headers; a corrupted key cannot escape the storage root (test).
7. Setting `COMFYUI_BASE_URL` alone no longer selects an unusable stub (KI-18): `IMAGE_PROVIDER` is explicit, default `mock`; `/health/providers` shows the selected provider.
8. The spike decision record exists with measured numbers **from the user's run**, and the real adapter passes the contract suite against synthetic fixtures; one recorded real-generation run is documented (not asserted in CI).
9. The Visuals page shows grid, status, regenerate, compare, set-current, and the blocked state when the gate is closed.

## Deliverables

Migration + `Asset` model changes; `visual/` modules (assets, prompt compiler, presets, bible, comfyui/adapter, workflows, imageinfo); `schemas/visual.py`; routes; settings (`IMAGE_PROVIDER`, `IMAGE_TIMEOUT_SECONDS`, `IMAGE_CONCURRENCY`, ComfyUI workflow/checkpoint names) + `.env.example`; Visuals page and components; tests/fixtures; spike script + decision record; **docs updated:** `docs/reference/status.md` (image generation, assets versioning, KI-17/18/9 rows), [image generation](../docs/domains/image-generation.md), [visual system](../docs/domains/visual-system.md), [character system](../docs/domains/character-system.md), [asset data model](../docs/data/asset-data-model.md), [API resources](../docs/api/README.md) (characters/locations/assets), [environment reference](../docs/reference/environment-reference.md), changelog.

## Dependencies

Depends on P0, P2, P5. Required by P8 (image assets + `content` route), P9 (Visuals stage views), P10.

## Do NOT (P6)

- Do not generate any image before the storyboard (and Visual Bible) are approved.
- Do not let a model choose seeds, sizes, filenames, versions or `is_current`.
- Do not hard-code a checkpoint, model name or provider in code; do not auto-download model files.
- Do not add `CharacterVersion`, Pillow, or reference-image conditioning without the decision above.
- Do not add AI *video* generation; do not create one asset per shot.
- Do not claim ComfyUI/any adapter works against a live service until a recorded run says so.

## Decision points (P6)

D-P6-1 Pillow dependency (above). D10 backend (spike). D-P6-2 whether reference-image upload ships in MVP (default: no). D-P6-3 base generation resolution and aspect (from spike + Bible). D-P6-4 whether the vector-illustration fallback (d) is pursued (product decision).

---

# Phase P7 — Voice, audio, subtitles (Checkpoint G)

## Goal

Every approved scene has a WAV narration whose duration is **measured by code**, processed by a documented deterministic policy (trim, pad, normalize, clip check); scene durations are resolved from measured audio; subtitle cues are generated deterministically from the text and the measured duration. Music, SFX, ducking and LUFS are **out of scope (P12)**.

## Why now

Audio durations are the input that makes the timeline truthful (replaces the 2–7 s estimate, KI-16) and subtitle timing depends on them. P7 is independent of P6 and runs in parallel after P5; P8 needs both.

## Prerequisites

P0, P2 (runs, provider wrapping), P5 (approved storyboard; `SceneVersion` narration text; `SceneSpec.subtitle` optional override). Reuses the asset-versioning migration and `GET /assets/{id}/content` from P6 (**if P7 starts first, P7 performs P6-T2 and P6-T9 and P6 reuses them** — implement each once).

## Backend

| Task | Work | Files |
| --- | --- | --- |
| **P7-T1 Spike S7 — TTS** | Define harness, measure, decide | NEW `scripts/spikes/tts_spike.py` (location undecided); decision record NEW `docs/decisions/ADR-0xx-tts.md` |
| **P7-T2 Voice adapter(s)** | WAV-only adapter(s); settings; selection | NEW `voice/<engine>.py`; MODIFY `voice/base.py` (`get_voice_provider`), `core/config.py`, `.env.example` |
| **P7-T3 Audio utilities** | Measure/trim/pad/normalize/clip-check with the standard library | NEW `voice/audio.py` |
| **P7-T4 `scene.voice` workflow** | Per-scene synthesis + processing + asset | NEW `voice/workflows.py`, NEW `voice/speech_text.py` |
| **P7-T5 Duration resolution (KI-16)** | Pure function replacing the estimate for final timelines | NEW `video/durations.py` (P8 integrates into Timeline v2; **do not** change `Timeline` shape here) |
| **P7-T6 `subtitles.build`** | Deterministic cue generation + SRT/VTT formatters | NEW `video/subtitles.py` |
| **P7-T7 Routes** | Voice run/regenerate, audio summary, voice settings | NEW `api/v1/audio.py`; MODIFY `api/v1/router.py` |
| **P7-T8 Frontend Audio stage** | Players, durations, warnings, regenerate, voice settings, subtitle preview | NEW `apps/web/src/app/projects/[id]/audio/page.tsx` + components |
| **P7-T9 Tests/fixtures** | Generated WAV fixtures, golden subtitle files | `apps/api/tests/…` |
| **P7-T10 Docs + status** | | `docs/…` |

### P7-T1 Spike S7 — method

Candidates (**examples**): a Piper-class CPU TTS, a Kokoro-class model, an XTTS-class model (heavier), a free-tier cloud TTS via a new adapter. Measure on 10 representative scene texts (20–60 words, with numerals, abbreviations, quotes): **real-time factor** `RTF = synthesis_seconds ÷ audio_seconds` (cold/warm), peak RAM, output format (sample rate, channels, sample width — we require **PCM WAV**), **determinism** (same text/voice ⇒ same samples?), failure modes. **Voice quality is judged by manual listening**; record notes — no automated claim. Arithmetic for the record: `total_synthesis ≈ video_audio_seconds × RTF` (e.g. a 12-minute narration, 720 s, at RTF 0.5 ≈ 6 minutes — illustrative, not a result). Decide engine, voice id, sample rate, concurrency.

### P7-T2 Voice adapter — contract

- Keep `VoiceProvider.synthesize(text, *, voice) -> VoiceResult`. **Contract tightening (documented + enforced by the shared contract test):** `mime_type == "audio/wav"`, PCM, mono or stereo, 16-bit. The service **re-measures** with `voice/audio.py`; if `abs(measured − result.duration_seconds) > 0.01 s` the asset fails with a clear error (the adapter's number is never trusted — D11).
- CLI engines (e.g. Piper-class) run via `subprocess` with an **argument list, no shell**; narration text goes on **stdin**, never in argv; fixed working dir under `data/temporary/`, timeout, stdout/size cap; model/voice path validated to live under a configured directory (`VOICE_MODEL_DIR`). HTTP engines use `httpx` with timeouts like the LLM adapters.
- Settings (NEW): `VOICE_PROVIDER` (`none` default | `mock` | engine name), `VOICE_MODEL_DIR`, `VOICE_ID`, `VOICE_TIMEOUT_SECONDS`.
- `FakeToneVoiceProvider` (NEW, `VOICE_PROVIDER=mock`): deterministic WAV (silence or sine; length = `words / 2.5` seconds) generated with `wave`; **labelled mock**; used by tests and dev, never claimed as speech. `UnconfiguredVoiceProvider` stays the default and keeps raising `ProviderNotConfiguredError`.

### P7-T3 Audio utilities (`voice/audio.py`) — specification

Stdlib only (`wave`, `array`, `math`). `audioop` is deprecated and removed in Python 3.13 — **do not use it**. Functions: `read_wav(bytes) -> WavInfo{sample_rate, channels, sample_width, frames, duration}` (rejects non-PCM/non-16-bit with `AudioFormatError`, mapped to `422`/failed asset), `peak_dbfs`, `rms_dbfs`, `clipping_ratio` (fraction of samples at ≥ 99.9 % of full scale), `trim_silence(threshold_dbfs, keep_head_ms, keep_tail_ms)`, `pad(head_ms, tail_ms)`, `normalize_rms(target_dbfs, max_gain_db, peak_ceiling_dbfs)`, `write_wav`. Pure functions on `array('h')`; per-scene audio (≈10 s at 22.05 kHz ≈ 220 k samples) makes pure-Python loops acceptable — **measure in the spike**; if too slow, **decision D-P7-1: add numpy** (default: no).

`AudioPolicy` (NEW frozen dataclass, `policy_version` string part of every voice `input_hash`): **initial values, tune in the spike and then freeze per version** — trim threshold −50 dBFS; keep head 80 ms / tail 200 ms; normalize to RMS −20 dBFS with gain limited to ±12 dB and peak ceiling −1 dBFS. These are placeholders for a documented, versioned policy — not standards; LUFS is P12.

### P7-T5 Duration resolution — specification

```text
resolve_scene_duration(measured_audio_seconds: float | None, narration: str, *, fps: int,
                       lead_in: float, tail_pad: float, min_visual_hold: float)
   -> ResolvedDuration{seconds, source: "measured" | "estimated"}
```

- `measured`: `seconds = ceil((audio + lead_in + tail_pad) × fps) / fps`, floored at `min_visual_hold` (initial 2.0 s, configurable). **No 7 s cap on measured audio** (this is KI-16's fix path).
- `estimated` (draft/preview only, flagged in the result): existing `estimate_duration`. **A final render requires `measured` for every scene** — P8 QA blocks otherwise.
- Resolved at **timeline build time** from the *current* voice asset; it is **not** written back into `SceneVersion` (immutable) and the model never supplies it.
- Typical visual pacing (≈2–7 s per beat) remains guidance for the storyboard/shot planner, never a clamp on narration length.

### P7-T6 Subtitle generation — specification

Deterministic, no provider. Input per scene: `text = SceneSpec.subtitle or narration`, `audio_seconds`, `SubtitlePolicy` (versioned: `max_chars_per_line` 42, `max_lines` 2, `min_cue_seconds` 1.0, `max_cue_seconds` 7.0, `lead_in`, punctuation weights — initial values). Steps: (1) normalize whitespace/quotes; (2) split into sentences on `. ! ? …` with an abbreviation guard list (`Mr.`, `Dr.`, `e.g.` …) and numeral decimals; (3) wrap sentences into cues respecting chars/lines, splitting long sentences at commas/semicolons then spaces; (4) merge cues shorter than `min_cue_seconds` into neighbours; (5) allocate time **proportionally to weighted character count** (chars + pause weight per `, ; . ? !`) across `[lead_in, lead_in + audio_seconds]`; (6) round to milliseconds; guarantee monotonic, non-overlapping, covering cues; (7) output `[{index, start, end, text}]` **relative to the scene** (the timeline adds the scene offset). `to_srt(cues, offset)` / `to_vtt(cues, offset)` pure formatters. Word-level alignment (forced alignment/whisper) is **P12**; proportional timing is an acknowledged approximation.

Persistence: per-scene cue document as `Asset(type=subtitle, mime=application/json)` with `input_hash = sha256(text, audio_seconds_rounded, subtitle_policy_version)` (so staleness follows the voice asset automatically). Cues are cheap and deterministic; the P8 timeline build may recompute them, but persisting makes them inspectable/editable in Studio and testable with golden files. Editing = set `SceneSpec.subtitle` (new `SceneVersion`) — there is no free-form cue editor in MVP.

## Database

No new tables. Uses the P6 `assets` columns (`version`, `is_current`, `input_hash`, `scene_version_id`) with `type=voice` and `type=subtitle` (both already in `AssetType`). `assets.meta` for voice: `provider`, `voice_id`, `engine_version`, `sample_rate`, `channels`, `duration_seconds` (**measured**), `peak_dbfs`, `rms_dbfs`, `clipping_ratio`, `trimmed_head_ms`, `trimmed_tail_ms`, `gain_db`, `policy_version`, `warnings[]`, `raw_sha256` (raw synth output is **not** stored as an asset; kept in `data/temporary/` only while debugging, with a cleanup rule). Voice settings live in `Project.settings["voice"]` validated by `VoiceSettings` (`voice_id`, optional `speed`) — a dedicated endpoint validates it because the generic PATCH does not validate nested settings (KI-4). Index on `(scene_id, type)` already covered by P6's partial unique index.

## API

| Endpoint | Purpose | Validation & errors | Idempotency |
| --- | --- | --- | --- |
| `PUT /projects/{id}/settings/voice` | Set `VoiceSettings` (single voice per project — voice consistency) | `422` bad body; `404` | Replace semantics; changing it makes all voice assets stale by hash |
| `POST /projects/{id}/voice` | Start `scene.voice` for scenes (`{scene_ids?, force?}`) → `202 {run_id}` | `409` storyboard not approved / voice settings missing / provider not configured (clear message); `422` | per-scene `input_hash` |
| `POST /scenes/{id}/voice` | Regenerate one scene's narration | same | same |
| `GET /projects/{id}/audio` | Summary per scene: current voice asset (duration, peak, warnings, stale), resolved duration + source, subtitle cues | `404` | read-only |
| `POST /projects/{id}/subtitles` | Start `subtitles.build` (usually auto-triggered after voice) | `409` if a scene lacks measured audio | `input_hash` |
| `GET /assets/{id}/content` | Audio/JSON playback (from P6; Range for `<audio>`) | as P6 | — |

SRT/VTT *export endpoints* need global timeline offsets and are delivered in P8 using the formatters built here.

## Frontend

- **P7-T8 Audio stage** — NEW `apps/web/src/app/projects/[id]/audio/page.tsx`: voice settings form (voice id; “provider not configured” banner with the setup link); per-scene row: narration text, `<audio controls src="…/assets/{id}/content">`, measured duration, resolved duration with `measured/estimated` badge, warning badges (clipping, silence, mismatch), stale badge, Regenerate; subtitle preview list under each scene (cue text + times); run progress (shared `RunProgress`). No waveform (optional later). Query keys `['project', id, 'audio']`, polling while a run is active.
- Empty/blocked states mirror P6.

## Services/Workflows

| Kind | Trigger | Inputs | Persisted output | Retry / idempotency |
| --- | --- | --- | --- | --- |
| `scene.voice` | API per scene / run | current `SceneVersion` narration → `speech_text`, `VoiceSettings`, `AudioPolicy` | `Asset(type=voice)` v N+1 + `is_current` flip | key `sha256(speech_text, voice_id, provider, engine_version, policy_version)`; same hash ⇒ no synth |
| `subtitles.build` | after voice asset becomes current, or API | `speech_text`/`subtitle`, measured duration, `SubtitlePolicy` | `Asset(type=subtitle)` JSON per scene | key above; pure function ⇒ always safe to re-run |
| `voice.generate_all` (run) | API | scene ids | progress `{done,total,failed}` | sequential (`VOICE_CONCURRENCY=1`), continue past failures, resumable |

**`scene.voice` algorithm:** gates → `speech_text(narration)` (deterministic: strip markup, normalize whitespace and curly quotes, small abbreviation/numeral rules defined in `voice/speech_text.py` and **iterated through golden tests** — it is *not* a full text-normalization engine) → hash/cache check → synth (timeout, ≤ 2 retries on transient errors; `ProviderNotConfiguredError` not retried) → `read_wav` (reject invalid/empty/zero-duration) → compare adapter vs measured duration → trim/pad/normalize per `AudioPolicy` → recompute stats → store `audio/<project_id>/<scene_id>/v<N>.wav` (`data/audio/`) → mark `ready` + flip current → trigger `subtitles.build`. **Clipping/silence are warnings in `meta.warnings` (surfaced by P8 QA), not failures**, except empty/invalid audio which fails.

## AI

None in P7 by design. Narration wording was decided in P5 (AI); everything here is deterministic. The only model-like component is the TTS engine (a provider), selected in the spike; its quality is judged manually. No LLM output may influence durations, timestamps or cue timing.

## Storage/media

WAV only (PCM 16-bit). Size arithmetic: 22.05 kHz mono 16-bit ≈ 44.1 KB/s ⇒ ≈ 32 MB for 12 minutes of narration (illustrative; actual sample rate comes from the engine). Keys `audio/<project_id>/<scene_id>/v<N>.wav`; subtitle JSON under the same pattern with `.json`. Remotion (P8) consumes WAV directly; no system FFmpeg is needed or planned (Remotion bundles ffmpeg/ffprobe; measuring WAV with `wave` avoids ffprobe entirely).

## Testing

- **Unit:** `read_wav` (valid, truncated, 8-bit/24-bit rejected, zero frames); `measure` equals `frames/sample_rate` on generated WAVs; trim/pad/normalize on synthetic signals (silence + tone + clipped tone) with exact expected sample counts and dBFS within tolerance; `clipping_ratio`; `resolve_scene_duration` table tests incl. frame rounding and “no cap for measured”; `speech_text` golden cases; subtitle splitter/allocator **golden files** (committed SRT/VTT for fixed inputs; assert monotonic, non-overlapping, within `[0, duration]`, deterministic across runs).
- **Contract:** shared `VoiceProvider` suite runs against `FakeToneVoiceProvider` and the real adapter's mocked transport/subprocess stub (subprocess tests use a tiny fake executable that writes a known WAV — no real model).
- **Workflow:** idempotent rerun = 0 synth calls; changed narration ⇒ new version, others untouched; adapter-vs-measured mismatch fails; invalid audio fails; gate closed ⇒ `409`; unconfigured provider ⇒ fast actionable failure.
- **API/frontend:** endpoints incl. `409/422/404`; Vitest for warning/stale/estimated badges; Playwright with mock voice: set voice → generate → durations appear → regenerate one → v2.
- **Determinism:** same inputs + `FakeToneVoiceProvider` ⇒ byte-identical processed WAV and identical cue JSON (hash equality test).

## Observability

Per-scene log: `workflow_id`, `project_id`, `scene_id`, `provider`, `voice_id`, `duration_ms`, `rtf` (synthesis ÷ audio seconds), `status`, `error`. Run progress counters; `/health/providers` reports selected voice provider and configured/ready. Warnings are first-class data (`meta.warnings`) so QA and Studio read them without parsing logs.

## Failure handling & idempotency

Same rules as P6: per-scene isolation, previous current preserved on failure, `interrupted` runs resumable, startup reconciliation of stale `generating` rows. Engine crash/non-zero exit/timeout ⇒ `failed` with sanitized error (stderr truncated, no paths/secrets). Output cap prevents runaway WAV size. Changing the voice settings or `AudioPolicy.policy_version` makes assets stale by hash — nothing is deleted.

## Acceptance criteria (Checkpoint G)

1. Gates: no synthesis before storyboard approval (`409`).
2. With `VOICE_PROVIDER=mock`, a fixture project yields one `ready`, `is_current` WAV per scene; each asset's `meta.duration_seconds` equals the value recomputed from the stored file (test).
3. Re-running generates **0** engine calls; changing one scene's narration regenerates that scene only.
4. `resolve_scene_duration` returns `measured` durations frame-aligned with **no 7 s cap**; a project with any `estimated` scene is flagged non-final.
5. Subtitle cues for every scene are monotonic, non-overlapping, within the scene's audio span, byte-identical across two runs, and match the committed golden SRT/VTT.
6. A clipped fixture is reported via `meta.warnings` and `clipping_ratio`; a silent/empty fixture fails the asset; neither crashes the run.
7. The spike decision record exists with measured RTF/RAM from the user's machine; the chosen real adapter passes the contract suite; one recorded real-engine run is documented. If **no** engine meets the criteria on the dev machine, the documented fallback is a cloud/free-tier adapter or `mock` for development — the phase is still “done” for Checkpoint G when the mock path and contracts pass and the decision is recorded.
8. The Audio page shows players, measured vs resolved durations, warnings, stale/estimated badges, regenerate, and voice settings.

## Deliverables

`voice/` (adapter(s), audio utilities, speech text, workflows), `video/durations.py`, `video/subtitles.py`, `api/v1/audio.py`, `VoiceSettings`/policies, settings + `.env.example` entries, Audio page + components, fixtures + golden files, spike script + decision record; **docs updated:** `docs/reference/status.md` (voice, subtitles, duration policy, KI-16 row), [voice and audio](../docs/domains/voice-and-audio.md), [subtitle system](../docs/domains/subtitle-system.md), [voice pipeline](../docs/media/voice-pipeline.md), [subtitle pipeline](../docs/media/subtitle-pipeline.md), [timeline system](../docs/domains/timeline-system.md), [API docs](../docs/api/README.md), [environment reference](../docs/reference/environment-reference.md), changelog.

## Dependencies

Depends on P0, P2, P5 (and the asset migration/content route from P6). Required by P8 (measured durations, subtitle cues, audio assets), P9 (Audio stage views), P10.

## Do NOT (P7)

- Do not let any model, adapter or config supply scene durations or cue times; measure and compute.
- Do not use `audioop`, shell invocation, or narration text in command-line arguments.
- Do not add music, SFX, ducking, LUFS, forced alignment or per-character voices here (P12).
- Do not depend on system FFmpeg/ffprobe.
- Do not claim speech quality or engine performance without the manual spike record.

## Decision points (P7)

D11 (WAV-only, measured by `wave`) is a contract. D-P7-1 numpy for audio processing (default no). D-P7-2 engine/voice/sample rate (spike). D-P7-3 initial `AudioPolicy`/`SubtitlePolicy` values (tune then freeze per version). D-P7-4 whether `scene.voice` auto-triggers `subtitles.build` or the UI does (default: auto).

---

## Cross-phase checks (before closing P6/P7)

- Asset migration implemented **once**; `content` route implemented **once**; both reused by P8.
- Staleness for images/voice/subtitles is computed by comparing stored `input_hash` with the recomputed hash ([design](versioning-and-invalidation.md)); no cascade writes.
- Nothing in P6/P7 changes `Timeline`/`TimelineScene`; P8 owns Timeline v2 and the `staticFile`-based asset resolution (D12).
- `make lint`, `make test` (DB tests actually run), `make e2e`, and a fixture render (after P8) stay green; nothing committed or pushed unless the user asks.
