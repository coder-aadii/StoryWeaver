# Phase P9 — Studio Workflow

> Execution plan for the Studio: the ten-stage production workspace that lets a user drive, inspect, edit, approve, regenerate and version every intermediate artifact of a project (Checkpoint I).

## Status

Planned. The Studio is **Partially implemented as a placeholder only**: `/studio` renders the Remotion Player on the bundled sample timeline and has no connection to any project; `/projects/[id]` shows seven static "Not implemented yet" cards. See [`docs/frontend/studio.md`](../docs/frontend/studio.md) and [`docs/reference/status.md`](../docs/reference/status.md). Nothing below is built. Master plan: [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md); artifact/staleness semantics: [`versioning-and-invalidation.md`](versioning-and-invalidation.md).

**Important framing — P9 unifies, it does not create.** Every earlier phase ships a *minimal stage view* for its own artifacts so the phase is demonstrable (P1: source + transcript view; P3: analysis viewer; P4: candidate list + approve button; P5: script/storyboard editor; P6: image grid; P7: audio list; P8: timeline preview + render button). Those views are built from the shared components defined in task P9-T2, which each earlier phase may create *first* (they are listed here as the canonical definitions). P9 adds what only makes sense once the stages exist together: the stage navigator, the aggregate `stages` endpoint, version history/compare/restore, dependency and staleness display, cost roll-ups, run progress and the cross-stage E2E flows.

## Current baseline (verified in `apps/web`)

| Fact | Evidence |
| --- | --- |
| 11 routes; only `/projects` has a mutation (create) | `src/app/**`, `projects/page.tsx` |
| `/studio` = Remotion `Player` on `sampleTimeline`; no project data | `src/app/studio/page.tsx` |
| `/projects/[id]` = title/status + 7 static cards (Analysis, Script, Storyboard, Visuals, Voice, Render, QA) | `src/app/projects/[id]/page.tsx` |
| Server state = TanStack Query keyed by API path (`staleTime` 10 s, `retry` 1); `ResourceList` is read-only | `components/providers.tsx`, `resource-list.tsx` |
| Zustand holds only `sidebarOpen` | `lib/store.ts` |
| API client = `api<T>()` + hand-written interfaces; `ApiError` has `status` + generic message (API `detail` is not parsed) | `lib/api.ts` |
| Tests: Vitest (jsdom, `@/` alias), Playwright with `webServer: pnpm dev`, `PLAYWRIGHT_CHROMIUM_PATH` for unsupported distros | `vitest.config.ts`, `playwright.config.ts`, `e2e/navigation.spec.ts` |
| Web dev server on 3100; `NEXT_PUBLIC_API_URL` must be in `apps/web/.env.local` | [KI-21](../docs/reference/status.md#known-issues-and-limitations) |

## Goal

A user opens a project and moves through **SOURCE → RESEARCH → STORY → SCRIPT → STORYBOARD → VISUALS → AUDIO → TIMELINE → QA → RENDER**. At each stage they can **inspect** the artifact, **edit** it (creating a new version), **approve** gated artifacts, **regenerate** it (whole stage, or one scene/asset where granularity exists), **compare/restore** versions, see **why something is stale**, see **cost so far**, and watch **running jobs** with errors and retry — never a single opaque "Generate video" button. Stage semantics follow [`docs/frontend/studio.md`](../docs/frontend/studio.md) and [`docs/product/user-flows.md`](../docs/product/user-flows.md).

## Why now

The Studio can only be unified once artifacts exist for every stage and the version/staleness model has been in use (P5–P8). Building it earlier would duplicate per-phase views; building it later would leave users inspecting JSON. It must precede hardening (P10) because the end-to-end failure-injection and 10× fixture-run tests drive the UI.

## Prerequisites

- P5 versioning core (`artifacts`, `artifact_dependencies`, `ScriptVersion`/`SceneVersion` endpoints, staleness computation) — [`versioning-and-invalidation.md`](versioning-and-invalidation.md).
- P2 `workflow_runs` + `GET /api/v1/runs/{id}` (D1) and `llm_calls` usage records (D2).
- P4 approval endpoints (D4); P6 asset endpoints + per-scene regeneration; P7 audio/subtitle artifacts; P8 timeline + render endpoints.
- P0: API error mapping (KI-8) and the Timeline v2 contract test (KI-7) so the Player and renderer agree.

## Backend

Mostly aggregation; no new generation logic.

| Task | Files | Work |
| --- | --- | --- |
| **P9-T1** Stage aggregate | `apps/api/app/studio/service.py` NEW, `apps/api/app/api/v1/studio.py` NEW, `schemas/studio.py` NEW; MODIFY `api/v1/router.py` | `build_stage_summary(project_id)` computes, per stage, the state `missing\|fresh\|stale\|running\|failed`, `current_version`, `approved` (bool), `stale_reason`, `latest_run_id`, `last_error`. **All values are derived from existing artifact/version/asset/run rows plus the staleness function from P5 — nothing new is stored.** State precedence: `running` > `failed` (latest run failed and no newer success) > `stale` > `fresh` > `missing`. |
| **P9-T2** Usage roll-up | `studio/service.py`, `api/v1/studio.py` | `GET /projects/{id}/usage`: sums `llm_calls` (tokens, estimated cost, cached-hit count) by stage/task. Estimated cost is explicitly labelled an estimate (provider price tables are config, not code). Requires KI-2 closed so token fields are not redacted in logs (DB rows are unaffected). |
| **P9-T3** Version listing & restore | `api/v1/artifacts.py` (P5; MODIFY if present), `studio/service.py` | Uniform `GET /projects/{id}/versions?stage=&subject=` returning `{version, created_at, created_by(user\|ai\|restore), summary, status, input_hash}`; restore = create a **new** version copying an old one's `data` (history is immutable — never rewrite). |
| **P9-T4** Optimistic concurrency | all `PATCH`/`POST …/versions` endpoints used by the Studio | Edits send `base_version`; a mismatch returns `409` with `{current_version}`. (Also fixes the "null → misleading 409" ambiguity for these endpoints by returning a typed error body — see KI-4 handling in [`01-foundation.md`](01-foundation.md).) |
| **P9-T5** Run listing | `api/v1/runs.py` (P2; MODIFY) | `GET /runs?project_id=&status=` for the activity drawer; `POST /runs/{id}/retry` (idempotent: reuses the run's `idempotency_key`; returns existing result if already succeeded). |

## Database

Intentionally **none** beyond what P2/P4/P5 created (`workflow_runs`, `llm_calls`, `artifacts`, `artifact_dependencies`, `*_versions`). One candidate index (decide when measuring, not before): `workflow_runs(project_id, created_at desc)` for the activity drawer. If staleness computation proves too slow for the stages endpoint on large projects, a cached `stage_state` column is a **Decision point**, not a default — recompute-on-read is the baseline ([`versioning-and-invalidation.md`](versioning-and-invalidation.md)).

## API

All under `/api/v1`, no authentication (localhost; D14), JSON.

| Endpoint | Purpose | Notes |
| --- | --- | --- |
| `GET /projects/{id}/stages` | Aggregate for the navigator | Response: ordered list of 10 `{stage, state, current_version, approved, stale_reason, latest_run_id, last_error}`; `404` unknown project. Cheap enough to poll every 2 s while any stage is `running`. |
| `GET /projects/{id}/usage` | Cost/usage per stage and total | Cached-hit counts included; estimates labelled. |
| `GET /projects/{id}/versions?stage=&subject=` | Version history for an artifact | `subject` = scene id / asset id / artifact id where applicable. |
| `POST /projects/{id}/stages/{stage}/regenerate` | Regenerate a stage | Body `{scope: "stage"\|"item", item_id?, mode: "keep_dependents"\|"mark_stale"}`; returns `202 {run_id}`. **Idempotent** via `Idempotency-Key` header or derived key from `(project, stage, scope, item, input_hash)`; precondition failures (unapproved gate, missing upstream) return `409` with a machine-readable `reason`. Delegates to the phase-owned workflow functions; P9 adds no generation code. |
| `POST /artifacts/{id}/approve` , `…/unapprove` | Approval gates (P4/P5, D4) | Consumed, not defined here. |
| `GET /runs/{id}` , `GET /runs?project_id=` (P1 defines `?subject_id=`; P2/P9 add `project_id` and `status` filters), `POST /runs/{id}/retry` | Progress and retry | `GET /runs/{id}` response: `{status, progress: {step, done, total}, error, attempts}` (D1). |
| existing | `GET /projects/{id}`, resource list/get endpoints | unchanged |

Error cases to specify in the OpenAPI response models: `404` (unknown project/stage), `409 stale_base_version`, `409 gate_not_approved`, `409 upstream_missing`, `422` invalid scope. Error bodies are typed (`{code, message, details}`); the web client parses them (see P9-T7).

## Frontend

### Routes (decision: nest Studio under the project)

`/studio` stays as a short-lived redirect/launcher (list projects → open one). The workspace lives at **`/projects/[id]/studio/[stage]`**, with `/projects/[id]` becoming a summary that links into it.

| File | Status |
| --- | --- |
| `apps/web/src/app/projects/[id]/studio/layout.tsx` | NEW — stage navigator + activity drawer + cost badge |
| `apps/web/src/app/projects/[id]/studio/[stage]/page.tsx` | NEW — dispatches to the stage component by slug (`source`,`research`,`story`,`script`,`storyboard`,`visuals`,`audio`,`timeline`,`qa`,`render`) |
| `apps/web/src/app/projects/[id]/page.tsx` | MODIFY — replace the 7 static cards with live stage summary linking to the workspace |
| `apps/web/src/app/studio/page.tsx` | MODIFY — project picker; keep the sample-timeline `Player` only as a labelled demo card (it is the current verified preview) |
| `apps/web/src/components/studio/` | NEW — `StageNav`, `ArtifactViewer`, `VersionHistory`, `ApprovalBar`, `RunProgress`, `CostBadge`, `StaleBadge`, `RegenerateMenu`, `ActivityDrawer`, plus per-stage components in `components/studio/stages/` (one file per stage, reusing earlier phases' minimal views) |
| `apps/web/src/lib/studio/` | NEW — `queries.ts` (query-key factory + hooks), `types.ts`, `stages.ts` (ordered stage metadata) |

The exact component file split is a suggestion; follow the existing naming (`kebab-case.tsx`) and check what earlier phases already created before adding files.

### State rules

- **TanStack Query = all server state** (stages, artifacts, versions, usage, runs). Never copy server data into Zustand.
- **Zustand = UI-only**: selected version id per artifact (for compare view), open panels/drawers, compare-mode toggle, per-session "dismissed warning" flags. Extend `lib/store.ts` (MODIFY) or add `lib/studio/store.ts`; keep slices small.
- **Query keys** — keep the **existing path-style convention** (`["/projects", id]` in `projects/[id]/page.tsx`, `[path]` in `ResourceList`, and `['/runs', id]` already planned by P1's `use-run.ts` in [`02-source-library.md`](02-source-library.md)). One factory in `lib/studio/queries.ts` extends it: `["/projects", id]`, `["/projects", id, "stages"]`, `["/projects", id, "usage"]`, `["/projects", id, "versions", stage, subject]`, `["/artifacts", artifactId]`, `["/runs", runId]`, `["/runs", { projectId }]`. Reuse P1's run hook rather than creating a second one.
- **Invalidation:** when `RunProgress` observes a run reach a terminal state it invalidates `["/projects", id, "stages"]`, `["/projects", id, "usage"]` and the affected artifact/version keys — and nothing else. Mutations (edit/approve/regenerate) invalidate `stages` immediately and rely on polling for the run result. Polling: `refetchInterval` 2 s on `["/runs", id]` and on `stages` **only while** something is `running`; otherwise the default `staleTime`.
- **Optimistic UI** only for edits (rollback on `409 stale_base_version` with a "reload latest / keep mine as new version" choice); approvals and regenerations wait for the server.

### API client typing (decision)

Recommend **`openapi-typescript` as a NEW devDependency** generating `src/lib/api-types.ts` from the FastAPI `/openapi.json` (script `pnpm gen:api` in `apps/web`, run against a local API; committed output so the web build does not need the API). Rationale: the Studio touches ~15 endpoints and the Pydantic models are the contract (KI-7 shows hand-mirroring drifts). Alternative: keep hand-written interfaces in `lib/api.ts` (current approach) and add contract tests — acceptable if the dependency is unwanted. **Decision point D-P9-1**; default = generate. In both cases extend `ApiError` to carry the parsed `{code, message, details}` body (MODIFY `lib/api.ts`) — today it discards the API `detail`.

### Per-stage inspector behavior

| Stage | Artifact(s) shown | Edit | Approve gate | Regenerate scopes |
| --- | --- | --- | --- | --- |
| SOURCE | Source metadata, current transcript, usage | Re-add/replace transcript (new transcript version) | — | re-fetch metadata/transcript |
| RESEARCH | Source analysis: facts/events/entities/themes, narrative opportunities | Edit/hide items (new analysis version) | — | stage |
| STORY | Story candidates, selected candidate, story architecture | Edit architecture beats | **Candidate selection** (default gate) | stage; candidate |
| SCRIPT | Script vN with validation report | Text edit → new `ScriptVersion` | Script acceptance (D4) | stage |
| STORYBOARD | Scenes/shots (`SceneSpec` per `SceneVersion`) | Per-scene edit → new `SceneVersion` | **Storyboard approval** (gate before expensive generation) | stage; scene |
| VISUALS | Visual Bible, characters, image per scene with versions | Edit prompt / bible | — | image (one scene); bible |
| AUDIO | Voice per scene (measured duration), subtitle cues | Edit narration text → re-synthesize | — | voice (one scene); subtitles |
| TIMELINE | Timeline v2 JSON (read-only, deterministic) + Player preview | — (code owns timing) | — | rebuild (cheap, deterministic) |
| QA | Deterministic QA report (P8) | — | — | re-run |
| RENDER | Renders list, output MP4, errors | — | — | new render |

The Timeline stage is intentionally **not editable**: durations/starts are code-owned ([ADR-004](../docs/decisions/ADR-004-ai-vs-deterministic-responsibilities.md)); the user changes the narration/storyboard and the timeline rebuilds.

## Services / Workflows

- P9 introduces **no new workflows**; `regenerate` dispatches to existing phase workflows through the runner (`app/workflows/runner.py`, `LocalRunner`) using the same idempotency keys ([retry table](../docs/workflows/retry-and-recovery.md)).
- Regeneration policy flag `mode`: `keep_dependents` (default for items such as one image: dependents stay pinned and are shown with a `StaleBadge` only if the staleness function says their inputs changed) or `mark_stale` (explicit). The staleness function — not the UI — decides what is stale ([`versioning-and-invalidation.md`](versioning-and-invalidation.md)).
- Preconditions (e.g. no image/voice generation before storyboard approval) are enforced **server-side**; the UI merely disables the control and shows the `reason`.

## AI

None added. Studio displays model/provider/prompt version recorded on each artifact/call (from `llm_calls`) and the cache-hit flag, so users can see "why was this free". It never calls providers directly (keys stay server-side).

## Storage / media

- Preview of images/audio requires serving files from `data/` — **KI-17**: no route does today. P9 depends on the P8 decision (D12: render uses a Remotion public dir). For **Studio preview** add `GET /api/v1/assets/{id}/content` (NEW, P6 or P9 whichever lands first; streams via `LocalStorage.open`, `Content-Type` from `mime_type`, `Range` support for audio, path-traversal-safe by key lookup — never a user-supplied path). Decision point D-P9-2 if P6 already added it.
- The Timeline stage `Player` reads Timeline v2 whose asset keys are resolved to those content URLs **in the web layer only** (the stored/rendered timeline keeps project-relative keys).
- No file upload from the Studio beyond transcript upload (P1).

## Testing

| Layer | Tests (NEW unless noted) |
| --- | --- |
| Vitest (components) | `StageNav` renders ten stages with state badges and marks the active one (`aria-current`); `StaleBadge` shows `stale_reason`; `ApprovalBar` disabled with reason when preconditions fail; `VersionHistory` lists versions, selects two for compare, "restore" calls the create-version endpoint (mocked `fetch`); `RunProgress` polls and stops on terminal state and invalidates the right keys (fake timers + `QueryClient`); `ApiError` parses typed error body (MODIFY `api.test.ts`) |
| Vitest (state) | Zustand slice: selected version, compare toggle; no server data in store |
| API (pytest, in P9 backend tasks) | `stages` state derivation matrix (missing/fresh/stale/running/failed precedence); `usage` roll-up sums cached/uncached calls; `regenerate` idempotent replay returns same `run_id`; `409` for unapproved gate / stale base version; version restore creates a new version and leaves old rows untouched |
| Playwright E2E | Against a **seeded API using the fake provider** (no network). Seed script NEW `scripts/seed_studio.py` (or `apps/api/app/dev/seed.py` — decide with `01-foundation.md` conventions) creates fixture projects *at each stage* (empty, after story candidates, after script, after storyboard, after images/audio, after render using fixture assets). Flows: (1) navigate all ten stages; (2) approve a candidate → script stage unlocks; (3) edit a scene → new version appears, dependents flagged stale; (4) regenerate **one** scene image → only that image changes version; (5) run fails (fault-injecting fake provider) → error shown → retry succeeds; (6) cost badge updates; (7) restore an old script version creates v(n+1). Playwright runs with `PLAYWRIGHT_CHROMIUM_PATH` on this OS ([e2e docs](../docs/testing/e2e-testing.md)). Playwright `webServer` config MODIFY to start both API (on a test DB) and web, or document the manual two-process setup. |
| Accessibility | Keyboard navigation through `StageNav`; focus management after approve/regenerate; `role="status"` for run progress, `role="alert"` for errors (existing `ErrorState`); automated axe check optional (NEW dev dependency — decision) |

## Observability

- Client: surface `run_id` and `code` in error toasts/messages so a failure can be matched to API logs (`workflow_id`).
- Activity drawer (`ActivityDrawer`) lists recent `workflow_runs` for the project with status/duration/attempts and links to the stage; this is the first user-visible observability surface (P10 extends it).
- No client-side analytics or third-party telemetry (local-first).

## Failure handling & idempotency

- A failed run leaves the stage `failed` with the persisted error; the previous successful version remains `current` (a failed regeneration never destroys the working artifact). Retry = `POST /runs/{id}/retry`; double-clicking Regenerate returns the same `run_id` (idempotent key), so duplicated clicks cannot double-spend tokens.
- `409 stale_base_version` on edit never loses the user's text: offer "save mine as a new version on top of latest".
- Network loss mid-poll: `ApiError(status 0)` is shown non-destructively (banner), polling resumes automatically.
- API restarts during a run: reconciliation (D1) marks the run `interrupted`; the UI shows it with a Retry action.
- Empty, loading and error states for every stage (reuse `EmptyState`, `LoadingRows`, `ErrorState`); a stage in `missing` state shows what upstream approval is needed and a deep link to it.

## Acceptance criteria (Checkpoint I)

1. `GET /projects/{id}/stages` returns all ten stages with correct states for each seeded fixture project; the precedence rules are covered by tests.
2. From the UI, on the seeded API with the fake provider, a user can: select a story candidate (approval persisted), see script v1, edit it to create v2, approve the storyboard, regenerate **only scene N's image** (other assets unchanged, asserted by version ids), see downstream render marked stale with a reason, rebuild the timeline, start a render and watch progress to completion.
3. Triggering generation before the required approval is impossible in the UI **and** rejected by the API with `409 gate_not_approved` (tested without the UI).
4. Version history shows v1/v2… for script and scenes (and image versions), compare view shows both, restore creates a new version and does not mutate old versions.
5. A forced provider failure shows the error on the stage, keeps the previous version current, and retry succeeds without duplicate artifacts.
6. Project cost badge equals the sum of `llm_calls` for the project; cache hits are counted separately.
7. Playwright E2E flows (1)–(7) above pass locally; Vitest and pytest additions pass; `make lint` clean; no `any` introduced.
8. `docs/frontend/studio.md`, `docs/reference/status.md` (Studio row, "ten-stage workspace" row) updated to reflect what exists.

## Deliverables

Stage aggregate + usage + versions + regenerate endpoints; `components/studio/*` and `lib/studio/*`; ten stage views composed from shared components; seed script and fixture projects; Playwright suite; typed API error handling; updated docs/status.

## Dependencies

- **Depends on:** P2, P4, P5 (hard); P6, P7, P8 (for their stage panels — stages for unfinished phases render as `missing`, so P9 work can begin per-stage as phases land).
- **Depended on by:** P10 (hardening drives the UI), P11 (library UI reuses `ArtifactViewer`/`RunProgress`).

## Task list (ordered)

| ID | Task | Depends on |
| --- | --- | --- |
| P9-T1 | `stages` aggregate service + endpoint + state-derivation tests | P5 staleness fn, P2 runs |
| P9-T2 | Shared components (`ArtifactViewer`, `VersionHistory`, `ApprovalBar`, `RunProgress`, `CostBadge`, `StaleBadge`, `RegenerateMenu`) + Vitest tests (may be created earlier by P1–P8 views; reconcile here) | — |
| P9-T3 | `usage` roll-up endpoint + `CostBadge` wiring | P2 `llm_calls`, KI-2 |
| P9-T4 | Version listing + restore-as-new-version endpoints | P5 |
| P9-T5 | Optimistic concurrency (`base_version`) + typed error bodies + `ApiError` parsing | P0 KI-8 |
| P9-T6 | Routes: `projects/[id]/studio/[stage]`, layout with `StageNav` + `ActivityDrawer`; rework `/projects/[id]` and `/studio` | T1 |
| P9-T7 | API typing decision D-P9-1 (generate or hand types) + query-key factory + polling/invalidation hooks | T1 |
| P9-T8 | `regenerate` endpoint (scopes, modes, idempotency, preconditions) delegating to phase workflows | P4–P8 workflows |
| P9-T9 | Asset content endpoint + Player asset URL resolution (if not already from P6/P8) | KI-17 / D12 |
| P9-T10 | Per-stage panels wired for stages whose phases have landed | phase-dependent |
| P9-T11 | Seed script + fixture projects at each stage | T1 |
| P9-T12 | Playwright E2E flows (1)–(7) + a11y checks | T6–T11 |
| P9-T13 | Docs/status update | all |

## Decision points

- **D-P9-1** typed client generation (`openapi-typescript`) vs hand-written types — default generate.
- **D-P9-2** (resolved by the master plan): `GET /assets/{id}/content` is introduced in **P6-T9** ([05](05-visuals-and-audio.md)); P9 only consumes it.
- **D-P9-3** whether `stage_state` stays recompute-on-read (default) or is cached after measurement.
- **D-P9-4** stage-level "approve" for scripts (an explicit gate) vs implicit acceptance by proceeding — default explicit, matching D4.
- Real-time updates via SSE instead of polling — deferred (D13).

## Must not change

- Preview must keep using the **same** Remotion composition as render ([`docs/frontend/studio.md`](../docs/frontend/studio.md) constraint); do not fork a separate preview renderer.
- The UI never computes durations or start times as truth; it displays server timelines.
- No provider keys or provider SDKs in the browser.
- No full timeline editor (Deferred until required by the production workflow).
