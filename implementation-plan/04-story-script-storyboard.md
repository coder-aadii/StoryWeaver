# P4–P5: Story Candidates, Script and Storyboard

> Execution plan for turning an analysed source into an **approved story**, a **validated script** and an **approved storyboard** of versioned scenes — the last two creative gates before any expensive image/voice spend.

## Status

Planned. Current state, verified against the code: **Partially implemented (tables and schemas only).** `Script`/`ScriptVersion`, `Scene`/`SceneVersion`, `ProjectSource`, `Project.settings` and the `SceneSpec` Pydantic model exist; `apps/api/app/story/__init__.py` is a one-line docstring; **no** story, script or storyboard code, prompt, route, service, validator or UI exists; `scene_versions.data` is not validated on write and neither `*_versions` table has an API; `project_sources` has no endpoint; `SceneVersion`/`ScriptVersion` have no approval or provenance beyond `script_versions.prompt_version/provider/model`. See [`status.md`](../docs/reference/status.md).

This file covers two phases of [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md): **P4** (Checkpoint D) and **P5** (Checkpoint E). The version/staleness mechanics both rely on are specified once in [`versioning-and-invalidation.md`](versioning-and-invalidation.md) — not repeated here.

## Shared assumptions (read first)

- **Built by P2 (assumed, verify in the code before starting):** tables `workflow_runs`, `llm_calls`, `artifacts`, `artifact_dependencies`; a task-routed LLM call helper that returns validated Pydantic output with repair/retry, caching by content hash and usage recording; a prompt registry under `packages/prompts/<name>/vN.md` with `prompt_version` recorded on every output; a `FakeLLMProvider` (recorded-fixture provider) for tests. **Built by P3:** artifacts of kind `source_analysis` and `narrative_opportunity_set` (with chunk references). **Built by P1:** `SourceVideo`/`Transcript`/`TranscriptChunk` population and source-status semantics.
- If P2 did not add `artifacts.lineage_id` (stable identity across edited versions), `artifacts.approved_by`, or the status values `proposed|approved|rejected|superseded`, **P4-T1** adds them. Do not create a second artifact mechanism.
- **Naming:** story/script/storyboard logic goes in the existing `apps/api/app/story/` package (NEW modules). Project-level helpers (gates, stage summary) go in a NEW `apps/api/app/projects/` package; hashing/versioning primitives in NEW `apps/api/app/core/versioning.py`. These locations are a recommendation consistent with [ADR-006](../docs/decisions/ADR-006-modular-monolith.md); if the repository has since adopted a different convention, follow it.
- **Identity rules** ([identifier mapping](../docs/domains/storyboard-system.md#identifier-mapping)): `scenes.id` (UUID) is the identity; `scenes.sequence` is ordering; `SceneSpec.scene_id` is a *derived display key* (`scene_001`…) that **code** assigns — no model ever supplies ids, sequence, durations or statuses.
- **Approval storage** extends [D4](IMPLEMENTATION_PLAN.md#7-technical-decisions-recommended-defaults): artifacts use `status='approved'`/`approved_at`/`approved_by`; the two versioned tables (`script_versions`, `scene_versions`) get the same trio plus `approval_current`. This is the same mechanism applied to the tables that already hold versions, not a new gate table ([gate options](../docs/domains/project-system.md#approval-and-gate-state-decision-pending): this plan realises option C's guarantees — accepted *version* recorded, revocable, auditable — without a separate table).

---

# P4 — Story candidates → approval gate → story architecture

## Goal

A user attaches a source to a project, asks for story candidates, **reads them, edits/approves exactly one (or rejects all)**, and gets a persisted **story architecture** (Hook → Setup → Development → Conflict/Tension → Escalation → Climax → Resolution, genre-variable) with deterministic word budgets. Nothing after the architecture can run until a candidate is approved. A source may legitimately yield *no suitable story*, and that is a first-class outcome.

## Why now

It is the first stage where AI output is *creative and user-facing*, so it is where the approval gate, the artifact lifecycle and the "cheap analysis → user choice → expensive writing" cost shape must be proven. It consumes P3's persisted, cached analysis, so it costs one cheap-model call per run. Script writing (strong model, many tokens) must not start before this gate exists ([cost strategy](../docs/ai/ai-cost-strategy.md)).

## Prerequisites

- P1 (sources/transcripts persisted), P2 (runtime, artifacts, routing, fake provider), P3 (`narrative_opportunity_set` artifact exists and is current for the project's source).
- P0 items: KI-3 (provider errors wrapped), KI-4 (PATCH validation, because project settings are patched), KI-8 (error→HTTP mapping, needed for `409 gate_not_satisfied`).

## Backend

**P4-T1 — Artifact lifecycle for candidates/architecture.** MODIFY `apps/api/app/models/domain.py` (or wherever P2 placed `Artifact`) and NEW Alembic revision: ensure `artifacts` has `lineage_id UUID`, `approved_by varchar(64)`, status values `proposed|approved|rejected|superseded`. Add partial unique indexes: one approved `story_candidate` per project and one approved `story_architecture` per project, e.g. `UNIQUE (project_id, kind) WHERE status='approved' AND kind IN ('story_candidate','story_architecture')`. Test: second approve in the same project violates the index unless the first is superseded in the same transaction.

**P4-T2 — Typed payloads.** NEW `apps/api/app/story/schemas.py` (Pydantic): `StoryCandidate` (title, premise, hook, central_question, protagonist_or_subject, conflict, stakes, beats[] (`label`, `summary`), climax, resolution, `source_grounding[]` (chunk ids + short quotes ≤ N chars), `estimated_duration_minutes` (**AI estimate, non-authoritative**), target_audience, tone, `self_assessment` (optional 1–5 scores, non-authoritative), `signals` (`source_overlap_ratio`, `similar_to[]`, both computed by code), `origin` = `ai|user`); `CandidateSet` (list + `outcome` = `candidates|no_suitable_story` + `reasons[]`); `StoryArchitecture` (`genre`, `acts[]` each with `beats[]`: `beat_id` (code-assigned `b01`…), `act` ∈ hook|setup|development|conflict|escalation|climax|resolution, `purpose`, `key_points[]`, `emotional_target`, `source_refs[]`, `weight` (AI relative importance 0–1), and code-computed `target_words`). Register payload models per `kind` in the P2 artifact validator registry.

**P4-T3 — Project settings schema.** NEW `ProjectSettings` in `apps/api/app/schemas/resources.py` (MODIFY `ProjectCreate/Update` to validate `settings`): `target_minutes` (default 12, 10–15), `tone` (str|None), `language` (default `en`), `candidate_count` (default 3, 1–5), **`auto_select_candidate` (default `false`)**. Unknown keys rejected. Existing rows with `{}` stay valid.

**P4-T4 — Project↔source attach.** NEW `apps/api/app/projects/service.py`: `attach_source(project_id, source_video_id, role)`, `detach_source`. Validation: source exists; source has a current `Transcript` with `status=ready` and chunks (else 409 `source_not_ready`). **MVP rule:** exactly one `primary` source may be used for candidate generation (multi-source is P11); the table already allows more — enforce in the service, not the schema.

**P4-T5 — Gate helper.** NEW `apps/api/app/projects/gates.py`: `require_approved(db, project_id, kind) -> Artifact` raises NEW `GateNotSatisfiedError(StoryWeaverError)` (add to `core/errors.py`; mapped to HTTP 409 with body `{"code":"gate_not_satisfied","gate":"G1","missing":"story_candidate"}`). Used by `story.architecture`, `script.generate`, and — via P5's helpers — every later expensive workflow. A precondition means "an approved version exists **and is the current version**"; editing an approved candidate creates a new version that is *not* approved ([approval rules](versioning-and-invalidation.md#approval-and-gates)).

**P4-T6 — Candidate workflow `story.candidates`.** NEW `apps/api/app/story/candidates.py`: `generate_candidates(project_id, count, guidance)` as a function submitted via the runner (kind `story.candidates`). Steps (all persisted): load project settings and the current `narrative_opportunity_set`; build prompt inputs (opportunity set summary + selected chunk excerpts by reference — never the whole transcript for local models); call the `story_candidates` task via the routed helper; validate against `CandidateSet`; run **deterministic validators** (below); persist each candidate as its own artifact (`proposed`, own `lineage_id`, `input_hash` = hash of opportunity-set content + guidance + count) and one `candidate_set` summary in the run result; if the model reports `no_suitable_story` or all candidates fail validation after repair, persist outcome `no_suitable_story` with reasons on the run (no candidate artifacts). Auto-select shortcut: only if `settings.auto_select_candidate` is true, pick by a deterministic rule (highest mean `self_assessment`, tie → first) and approve with `approved_by='auto:top_self_assessment'`; otherwise stop at `proposed`.

**P4-T7 — Candidate validators (deterministic).** NEW `apps/api/app/story/validators.py` (shared with P5): schema valid; ≥1 `source_grounding` chunk id per candidate and every id exists in the source's chunks; titles unique; pairwise token-set Jaccard of `premise` below a configurable threshold (candidates must be *independent*, not slices of one story — flags near-duplicates); `beats` count within bounds; banned meta-phrases; computes `signals.source_overlap_ratio` (share of word 5-grams of title+premise+beats found in the source text — a **quality metric, not a legal test**) and `signals.similar_to` (normalised title/premise 5-gram Jaccard against *approved* candidates of other projects — cheap lexical check; embedding similarity is P12). Hard failures trigger the repair loop; warnings are shown, never block.

**P4-T8 — Architecture workflow `story.architecture`.** NEW `apps/api/app/story/architecture.py`. Preconditions: `require_approved(project, 'story_candidate')`. Model call (`story_architecture` task, strong model) turns the approved candidate (**content as approved/edited, not the original**) + source grounding into acts/beats with `weight`s. Code then: assigns `beat_id`s; verifies required acts (hook, climax, resolution present; order respected; optional acts may be merged/omitted per genre); computes `total_words = round(target_minutes*60*WORDS_PER_SECOND)` from the existing constant (**labelled an estimate** — real length is measured from audio in P7) and `target_words` per beat ∝ `weight` with a per-act floor; persists as `story_architecture` artifact (`proposed`), then the user approves it (G1b) — or edits (creates v+1) before script generation. The artifact records the candidate artifact id+version it derived from (edge in `artifact_dependencies`).

**P4-T9 — Regenerate and edit semantics.** `POST …/generate` while candidates exist creates a *new run* and new `proposed` artifacts; older unapproved ones are marked `superseded` only if the user chose "replace" (default: keep, so nothing is lost). Editing an approved candidate → new version (`parent_id` = old), old stays `approved` history but is no longer current-approved; downstream artifacts become **stale-suggested** by hash comparison, never deleted.

**P4-T10 — Stage summary.** NEW `apps/api/app/projects/stages.py` implementing `GET /projects/{id}/stages` for stages `source`, `research`, `story` using the algorithm in [versioning-and-invalidation](versioning-and-invalidation.md#stage-summary-api); P5+ extend the same function.

## Database

| Item | Change | Notes |
| --- | --- | --- |
| `artifacts` | Reuse (P2). Possibly add `lineage_id`, `approved_by`, status values (P4-T1) | `story_candidate`, `story_architecture` kinds; payload validated by `StoryCandidate`/`StoryArchitecture` |
| Partial unique indexes | one approved candidate / architecture per project (P4-T1) | Postgres partial index via `postgresql_where` |
| `project_sources` | Reuse; **no schema change** | Service enforces single primary source for MVP |
| `projects.settings` | Reuse; validation in Pydantic only | Decision D-P4-1: typed columns rejected — `settings` is the designed extension point |
| `artifact_dependencies` | Reuse (P2): edge architecture→candidate, candidate→opportunity set | Display/lineage only; correctness comes from `input_hash` ([versioning](versioning-and-invalidation.md)) |

Migration: one revision `p4_artifact_lifecycle` (indexes/columns above). Test `upgrade → downgrade → upgrade` and `alembic check`.

## API

All routes under `/api/v1`, no authentication (localhost-only, D14). Mutating routes return `202 {run_id}` for workflows, `200/201` for direct edits. Errors: `404` unknown id, `409 gate_not_satisfied | source_not_ready | conflict`, `422` validation.

| Method + path | Purpose | Request / response concept | Validation & errors | Idempotency |
| --- | --- | --- | --- | --- |
| `POST /projects/{id}/sources` | Attach source | `{source_video_id, role="primary"}` → attachment | source ready (409 `source_not_ready`), duplicate attach is a no-op `200` | PK `(project, source)` |
| `GET /projects/{id}/sources`, `DELETE /projects/{id}/sources/{sid}` | List / detach | — | detach blocked (409) if approved candidate depends on it | — |
| `POST /projects/{id}/story/candidates/generate` | Run `story.candidates` | `{count?, guidance?, replace?}` → `{run_id}` | needs attached ready source and current analysis (409 `analysis_missing`: client should run P3 first); `count` 1–5 | run `idempotency_key` = hash(inputs + prompt_version + model); same inputs while one is running/finished returns that run |
| `GET /projects/{id}/story/candidates` | List candidates (+ outcome/reasons of last run) | artifacts of kind `story_candidate`, status filter | — | — |
| `POST /projects/{id}/story/candidates` | User-authored candidate (`origin=user`) | `StoryCandidate` body | same schema + grounding check | new lineage each call |
| `PATCH /artifacts/{id}` | Edit candidate/architecture | partial payload + `base_version` → **new version** | `409` if `base_version` ≠ current (optimistic concurrency); payload re-validated | — |
| `POST /artifacts/{id}/approve` / `/reject` | Gate action | `{acknowledge_downstream?: bool}` → artifact | approving a second candidate while downstream artifacts exist returns `409 downstream_exists` listing them; resubmit with `acknowledge_downstream=true` supersedes the prior approval, downstream becomes stale-suggested (not deleted) | re-approving the approved version is a no-op |
| `POST /projects/{id}/story/architecture/generate` | Run `story.architecture` | `{}` → `{run_id}` | `require_approved(story_candidate)` else 409 | key = hash(approved candidate content hash + target_minutes + prompt_version + model) |
| `GET /projects/{id}/story/architecture` | Current architecture + budgets | artifact | 404 if none | — |
| `GET /runs/{run_id}` | Poll workflow state | status, progress, error, result | (P2 route) | — |
| `GET /projects/{id}/stages` | Stage summary | see versioning doc | — | — |

## Frontend

NEW routes (follow existing conventions in `apps/web/src/app/...`, TanStack Query keyed by API path, `ResourceList`-style states):

- `apps/web/src/app/projects/[id]/story/page.tsx` (NEW): source picker (attach/detach), "Generate candidates" with count/guidance, run progress (polls `/runs/{id}`), candidate cards (premise, hook, conflict, stakes, beats, grounding quotes, signals badges), **Edit** (form → `PATCH`), **Approve** / **Reject**, "Regenerate", user-authored candidate form, explicit **"No suitable story"** panel showing reasons and next actions (attach another source, change guidance, write one manually). Auto-select is a project setting toggle, off by default, labelled "System will pick for you".
- Architecture section on the same page: act/beat list with target words, edit, approve.
- `apps/web/src/components/stage-nav.tsx` (NEW): shows the 10 stages from `/projects/{id}/stages` (state badges); P9 turns this into the full Studio navigation.
- MODIFY `apps/web/src/app/projects/page.tsx`: project creation also lets the user pick a source; MODIFY `projects/[id]/page.tsx`: replace the "Not implemented yet" stage cards for Story with real status (other stages keep the placeholder until their phase).
- State: server state in TanStack Query; no new Zustand store unless a cross-page UI state appears (decide then).

## Services/Workflows

| Workflow | Trigger | Inputs | Outputs / persisted | Retry & idempotency | Failure behaviour | Gate |
| --- | --- | --- | --- | --- | --- | --- |
| `story.candidates` | POST generate | project, opportunity set, settings, guidance | `story_candidate` artifacts or `no_suitable_story` outcome; `llm_calls` rows | Cache by content hash: unchanged inputs ⇒ 0 provider calls; retry only re-runs the failed model call | Provider/validation failure ⇒ run `failed` with error, project untouched | Output stops at `proposed` (user gate G1) |
| `story.architecture` | POST generate | approved candidate | `story_architecture` artifact | key above | repair loop ≤2, then `failed` | Requires G1; output is `proposed`, approval G1b |

Runs are executed by `LocalRunner` (D1); the function receives ids, re-reads state from the DB, and writes status transitions `queued → running → succeeded|failed|interrupted`.

## AI

- **Tasks / routing names (P2 owns the routing table):** `story_candidates` — routine-to-medium cost, structured output; `story_architecture` — higher quality. Models come from settings (`story_llm_model`, overridable per task); **no model name in code**. The P2 benchmark decides which configured provider serves which task; on this CPU-only machine a cloud/free-tier provider may be needed for `story_architecture` (unmeasured).
- **Prompts (NEW, `packages/prompts/story_candidates/v1.md`, `story_architecture/v1.md`):** include the output JSON Schema, the independence requirement ("each candidate must stand alone as its own story; do not split the source chronologically"), the "no suitable story is an acceptable answer" instruction, and the originality instruction ("new framing, structure and hook; do not reuse the source's phrasing"). Source text enters prompts only as delimited, quoted data (prompt-injection guard: instruct the model to treat it as untrusted content).
- **AI decides:** which narrative opportunities become candidates, premise/hook/conflict/stakes/beats wording, grounding selection, act structure, beat importance `weight`, genre, tone.
- **Deterministic code decides:** ids, versions, statuses, approval, chunk-id existence, uniqueness/independence checks, overlap/similarity *metrics*, word budgets (from `target_minutes` and `WORDS_PER_SECOND`), required-act checks, caching, which candidate is selected under the opt-in shortcut.
- **Validation/retry:** Pydantic parse → deterministic validators → at most 2 repair calls with the error list appended; then fail. Hard failures: schema, missing grounding, non-existent chunk id, duplicate candidates, missing required acts. Warnings: high overlap, `similar_to` hits.
- **Cost:** one candidates call per run (cached by hash), one architecture call per approval. No image/voice work possible before this gate.

## Storage/media

None (no binary assets). Candidate quotes are short excerpts stored inside artifact JSON; full text stays in `transcripts`/`transcript_chunks` and is referenced by chunk id.

## Testing

- **Unit:** Pydantic schema round-trips; each validator with pass/fail fixtures; budget allocation (sums to total within rounding, floors respected); n-gram overlap metric on known strings; `require_approved` truth table.
- **Database:** partial unique index prevents two approved candidates; supersede-then-approve in one transaction succeeds; migration up/down.
- **API:** every endpoint's 404/409/422 path; approve-with-downstream-exists flow; `PATCH` with stale `base_version` → 409.
- **Workflow (fake provider, recorded fixtures in `apps/api/tests/fixtures/story/*.json`, NEW):** happy path; second identical run makes **0 provider calls** (assert `llm_calls` count); malformed first response repaired on retry; permanent failure leaves no artifacts and a `failed` run; `no_suitable_story` path; auto-select off ⇒ nothing approved, on ⇒ `approved_by='auto:…'`; `story.architecture` without approval ⇒ 409 and no provider call.
- **Frontend:** Vitest for candidate card states (loading/empty/error/no-suitable-story); Playwright: attach source → generate (fake provider) → edit → approve → architecture appears; architecture button disabled until approval.
- **Not claimed:** no live-provider test. One recorded manual real-provider run is a P10 task.

## Observability

Log events `story.candidates.started|finished|failed`, `gate.approved|rejected` with `workflow_id`, `project_id`, `source_id`, `artifact_id`, `provider`, `model`, `duration`, `status`, `error` (token fields depend on KI-2 being fixed in P0). `llm_calls` rows give per-call tokens/duration/cache-hit; the project page shows the per-project total. Run results store validator warnings.

## Failure handling & idempotency

Idempotency keys are the P2 run keys listed in the API table (inputs + `prompt_version` + model; see [retry table](../docs/workflows/retry-and-recovery.md#idempotency-keys)). A failed run leaves the project and earlier artifacts untouched; retrying with the same key resumes at the failed model call because earlier successful calls are cache hits. Startup reconciliation marks orphaned `running` runs `interrupted`. Concurrent duplicate requests resolve to the same run. User edits use optimistic concurrency (`base_version`).

## Acceptance criteria (Checkpoint D)

1. Attaching a non-ready source returns 409; a ready one succeeds twice idempotently.
2. With the fake provider, `POST …/candidates/generate` yields N schema-valid, mutually independent candidates, each citing existing chunk ids; the run is visible via `GET /runs/{id}`.
3. Re-running with identical inputs makes **zero** provider calls (test asserts it).
4. `POST …/architecture/generate` returns 409 `gate_not_satisfied` until a candidate is approved; no provider call occurs.
5. Approving a candidate persists `approved_at/approved_by='user'`; approving a second one requires `acknowledge_downstream` when downstream exists and never deletes artifacts.
6. A `no_suitable_story` response is stored and rendered with reasons; no downstream work can start.
7. Architecture contains all required acts, in order, and `Σ target_words` equals the computed total within rounding.
8. Auto-select is off by default; enabling it approves with `approved_by` starting `auto:`.
9. `make lint`, `make test` (with `TEST_DATABASE_URL`), `make e2e` pass; migration is reversible.

## Deliverables

Story/architecture schemas, validators, two workflows, gate helper + 409 mapping, project-source and artifact-edit/approve routes, stage summary (source…story), story page + stage nav, fixtures and tests, two prompts at `v1`.

## Dependencies

Depends on P1, P2, P3 (+ P0 KI-3, KI-4, KI-8). **Blocks** P5 (script needs the approved architecture) and everything after. Shares the artifact/hash primitives with [`versioning-and-invalidation.md`](versioning-and-invalidation.md).

## Docs to update at phase end

[`status.md`](../docs/reference/status.md) rows (story generation, candidate approval gate, artifact versioning), [`story-generation.md`](../docs/domains/story-generation.md), [`project-system.md`](../docs/domains/project-system.md) (gate decision → recorded), [`story-data-model.md`](../docs/data/story-data-model.md) (storage option B chosen), [`api/`](../docs/api/README.md) (new resources), changelog.

## Do NOT

Do not slice the source by time or paragraph to make candidates; do not let a model assign ids/versions/approval/durations; do not run the architecture on the unedited candidate if the user edited it; do not auto-approve by default; do not delete unapproved or superseded artifacts; do not add multi-source support, embeddings or LLM-based similarity here (P11/P12); do not claim the overlap/similarity numbers are legal assessments.

## Decision points

- **D-P4-1** Typed settings via Pydantic over `Project.settings` (recommended) vs real columns.
- **D-P4-2** One approved candidate per project (recommended for MVP) vs several approved candidates producing several videos from one project (P11/P12 — would instead be several *projects* sharing a source).
- **D-P4-3** Thresholds (candidate Jaccard independence, overlap warning) default to warn-only constants; calibrate with real runs before making any a hard failure.

---

# P5 — Script + validation + storyboard + versioning core

## Goal

From the approved architecture, produce a **script** (10–15 minutes at the code's narration-rate estimate), validate it deterministically, let the user edit/approve a script version (G2), then generate a **storyboard**: ordered scenes, each with narration spans, visual plan, shots, camera spec and draft prompts, stored as validated `SceneVersion` rows. The user approves the storyboard (G3). After G3, the system may spend on images and voice.

## Why now

The script is the only artifact whose text everything downstream (voice, subtitles, scenes) derives from, and the storyboard is the last cheap-to-change artifact before expensive generation. This is also the first phase with **user-editable versioned content**, so the version/staleness core ([doc](versioning-and-invalidation.md)) lands here.

## Prerequisites

P4 accepted (approved `story_architecture`); P2 runtime; P0: KI-3, KI-4, KI-8, KI-7 not required yet. `SceneSpec` v2 must stay backward compatible with the Timeline v1 builder until P8.

## Backend

**P5-T1 — Versioning primitives.** NEW `apps/api/app/core/versioning.py`: `canonical_json`, `content_hash`, `generation_key`, `compute_state` exactly as specified in [versioning-and-invalidation](versioning-and-invalidation.md#algorithms). Unit-tested before anything uses them.

**P5-T2 — Migration `p5_versions_approval`.** `script_versions`: add `approved_at timestamptz null`, `approved_by varchar(64) null`, `approval_current boolean not null default false`, `input_hash varchar(64) null`, `kept_input_hash varchar(64) null`, partial unique `(script_id) WHERE approval_current`. `scene_versions`: same four plus `script_version_id uuid null FK script_versions(id) ON DELETE SET NULL`, `provider/model/prompt_version` (nullable, mirrors `script_versions`), partial unique `(scene_id) WHERE approval_current`, index `(scene_id, version DESC)`. `scenes`: add `deleted_at timestamptz null` (soft delete keeps versions and future assets). `scripts`: add `UNIQUE (project_id)` (one script per project in MVP; D-P5-1). Backfill is trivial (tables are empty today — verify).

**P5-T3 — Sentence segmentation.** NEW `apps/api/app/story/text.py`: deterministic sentence splitter (stdlib only; handles abbreviations conservatively) producing stable sentence ids `s001…` **per script version**, plus Unicode NFC normalisation. Golden tests with tricky punctuation.

**P5-T4 — Script content schema.** NEW in `story/schemas.py`: `ScriptContent` stored in `ScriptVersion.content`: `schema_version`, `acts[]` (`act`, `beat_ids[]`, `text`, `sentences[]` with ids), `full_text`, `word_count`, `word_budget` {total, per act}, `reading_time_seconds_estimate` (**flagged estimate**), `validation` (report below), `derived_from` {architecture_artifact_id, version, input_hash}.

**P5-T5 — Workflow `script.generate`.** NEW `apps/api/app/story/script.py`. Precondition `require_approved(project,'story_architecture')`. Code computes per-act word budgets from the architecture (already in `target_words`). For each act in order, call the `script` task (strong model) with: architecture beats for that act, the *summary* of previous acts' text (not full), tone/language, grounding excerpts by reference; validate the act's word count (±15% of budget — configurable) and hard validators; repair ≤2 times; persist after **each act** (partial script is recoverable: resume skips accepted acts by cache hit). On completion create `ScriptVersion` `n+1` (never overwrite) with `prompt_version/provider/model`, then run `script.validate`.

**P5-T6 — Validators `script.validate`.** MODIFY `story/validators.py`. Deterministic and pure; returns `ValidationReport{ hard_failures[], warnings[], metrics }`:
- *Hard:* schema; total word count within tolerance of budget; every required act present and ordered; every architecture beat covered (beat marker present — acts generated per beat with markers stored in `sentences[].beat_id`); no empty sentences; banned patterns (meta phrases such as "in this video", "as an AI", references to "the transcript/source says", markdown/stage-direction artifacts) from a constants list.
- *Warnings/metrics (never block):* `source_overlap_ratio` and `longest_verbatim_run` (word 5-gram shingles vs source transcript — **a quality metric, not a legal test**, thresholds Decision pending), sentence-length outliers, repeated n-grams, `reading_time_seconds_estimate` (= words / `WORDS_PER_SECOND`; **estimate**, real duration is measured in P7).
Validation also runs synchronously on user-submitted edits.

**P5-T7 — Script edit/approve.** NEW `story/script_service.py`: `save_version(script_id, content, base_version)` (re-segments, validates, creates v+1; 409 if `base_version` is not current), `approve_version(script_id, version)` (sets `approval_current` atomically, clearing the previous; requires zero hard failures). Approving a different version when a storyboard exists requires `acknowledge_downstream`; the storyboard becomes **stale-suggested** by hash (see versioning doc), never deleted.

**P5-T8 — SceneSpec v2 and AI draft schema.** MODIFY `apps/api/app/schemas/scene.py` (**backward compatible**): add `schema_version: int = 2`, `shots: list[ShotSpec] = []`, `script_span: ScriptSpan | None` (`from_sentence_id`, `to_sentence_id`, `span_hash`), `beat_id: str | None`, `narration_override: bool = False`, `characters_resolved`/`locations_resolved` left to P6. `ShotSpec` (NEW): `shot_key` (code-assigned `a`,`b`…), `purpose`, `camera: CameraSpec`, `weight` (AI relative importance of this shot within the scene; **not a duration**), `reuses_shot_key: str | None` (reuse an image with reframing). NEW `SceneDraft` (AI output; **no ids, sequence, scene_id, durations**): `script_span`, `beat_id`, `visual_intent`, `characters`, `locations`, `objects`, `action`, `emotion`, `camera`, `shots[]`, `image_prompt`, `negative_prompt`, `music`/`sfx` hints. v1 documents still parse (defaults). Do **not** change `Timeline`/`build_timeline` in this phase (P8). Contract test: JSON Schema export still generates; the zod mirror for scenes is not consumed by Remotion, so no zod change.

> **Shot representation (D-P5-2, decision):** the docs treat *Shot* as a future entity. Recommended: shots are a **validated list inside `SceneVersion.data`** (no new table) because shots have no independent lifecycle until P6/P8 assets reference them by `(scene_version_id, shot_key)`. Alternative: a `shots` table — stronger FKs for asset→shot, more migrations; revisit only if P6 needs per-shot assets queried independently. `CameraSpec.shot` (framing) stays distinct from `ShotSpec` (timeline shot) per the [glossary](../docs/reference/glossary.md).

**P5-T9 — Workflow `storyboard.generate`.** NEW `apps/api/app/story/storyboard.py`. Precondition `require_approved(project,'script')` (approved `ScriptVersion`). Design that keeps **AI = content, code = execution**: the model receives the script as sentences with ids and the architecture, and returns an ordered list of `SceneDraft`s that assign **contiguous, non-overlapping sentence spans** plus visual plans. Code then: verifies spans cover every sentence exactly once, in order (hard failure → repair); builds `narration` by *slicing the script text* (the model never rewrites narration); creates `Scene` rows (`sequence` 1…n, `script_id`) and `SceneVersion` v1 with `SceneSpec` v2 validated on write (`scene_id=f"scene_{sequence:03d}"`, `sequence` mirrored from the row, `duration=None`, `script_span.span_hash` computed); records `script_version_id`, `input_hash`, provider/model/prompt_version. Character/location names stay strings here; P6 resolves them against the Character/Location tables and the Visual Bible.
- *Scene count guidance:* code passes a target range derived from the word budget and the P4 beat weights (a scene is a narrative beat unit, not one sentence); out-of-range counts are a warning, not a hard failure.
- *Re-running* creates a new storyboard generation as new `SceneVersion`s on the same `Scene` rows where `script_span` text is unchanged (hash match) and new `Scene` rows otherwise, soft-deleting scenes whose span vanished — see [staleness rules](versioning-and-invalidation.md#policy-table).

**P5-T10 — Scene service.** NEW `story/scene_service.py` (validate on every write): `save_scene_version(scene_id, data, base_version)` (re-validates `SceneSpec`, asserts `scene_id`/`sequence` derive from the row, recomputes `span_hash` and sets `narration_override=true` if narration differs from the sliced span → reported as an informational divergence), `insert_scene(project_id, after_sequence)`, `delete_scene` (soft), `reorder(project_id, ordered_scene_ids)` (single transaction renumbering `sequence` 1…n; **ordering is structure, not content: no new `SceneVersion`**), `approve_storyboard(project_id)` (see gate below).

**P5-T11 — Storyboard gate G3.** `approve_storyboard` succeeds only if: an approved script version exists; every active scene's `script_span` is valid; coverage check passes (or divergences are acknowledged); no hard validation failures. It sets `approval_current` on the **current (highest) version of every active scene** in one transaction. G3 is satisfied iff every active scene's highest version is `approval_current`. Editing a scene afterwards creates an unapproved version, so only that scene needs re-approval; `require_approved(project,'storyboard')` (used by P6/P7 workflows) checks this.

**P5-T12 — Stage summary + staleness for script/storyboard.** Extend `projects/stages.py` per the versioning doc: script state (fresh/stale vs architecture hash), storyboard state with per-scene counts.

## Database

| Item | Change |
| --- | --- |
| `script_versions` | + `approved_at`, `approved_by`, `approval_current`, `input_hash`, `kept_input_hash`; partial unique on `(script_id) WHERE approval_current`. Reuses `content`, `prompt_version`, `provider`, `model` |
| `scene_versions` | + same approval trio/hashes, `script_version_id` FK, provenance columns; partial unique on `(scene_id) WHERE approval_current`; index `(scene_id, version DESC)`. `data` now validated by `SceneSpec` v2 on every write |
| `scenes` | + `deleted_at`; `sequence` stays non-unique (reorder is a transactional renumber) |
| `scripts` | + `UNIQUE (project_id)` |
| New tables | none (shots live inside `scene_versions.data`) |

One revision `p5_versions_approval`; reversible; `alembic check` clean. Existing generic `/scripts` and `/scenes` CRUD routes stay but must not be used to create versions (service only).

## API

All under `/api/v1`, no auth, localhost-only. Workflow routes return `202 {run_id}`.

| Method + path | Purpose | Request / response concept | Errors | Idempotency |
| --- | --- | --- | --- | --- |
| `POST /projects/{id}/script/generate` | Run `script.generate` | `{target_minutes?, tone?}` (defaults from settings) → `{run_id}` | 409 `gate_not_satisfied` (no approved architecture) | run key = hash(architecture content hash + params + prompt_version + model) |
| `GET /projects/{id}/script` | Current script (+ validation, approval state) | `ScriptVersion` + report | 404 | — |
| `GET /projects/{id}/script/versions` | Version list | id, version, provider/model/prompt_version, approved flag, validation summary | — | — |
| `POST /projects/{id}/script/versions` | Save an edited script as v+1 | `{content, base_version}` → version + validation report | 409 stale `base_version`; 422 hard validation failure is **returned as a report with `saved=true` but `approvable=false`** (the user may save work-in-progress) | — |
| `POST /projects/{id}/script/versions/{n}/approve` | Gate G2 | `{acknowledge_downstream?}` | 409 `hard_failures_present`, `downstream_exists` | re-approve = no-op |
| `POST /projects/{id}/storyboard/generate` | Run `storyboard.generate` | `{}` → `{run_id}` | 409 no approved script | key = hash(approved script content hash + prompt_version + model) |
| `GET /projects/{id}/scenes` | Active scenes with **current version**, approval flag and per-scene state | list | — | — |
| `GET /scenes/{id}/versions` | Scene version history | list | 404 | — |
| `POST /scenes/{id}/versions` | Edit scene → v+1 | `{data, base_version}` | 409 stale base; 422 `SceneSpec` invalid | — |
| `POST /projects/{id}/scenes` | Insert scene after `sequence` | `{after_sequence, data}` | 422 | — |
| `DELETE /scenes/{id}` | Soft delete | — | 404 | repeat = no-op |
| `POST /projects/{id}/scenes/reorder` | Reorder | `{ordered_scene_ids}` must be a permutation of active scenes | 422 | same input = no-op |
| `POST /projects/{id}/storyboard/approve` | Gate G3 | `{acknowledge_divergences?}` | 409 `storyboard_incomplete` / `hard_failures_present` | no-op if already approved |
| `GET /projects/{id}/stages` | Stage summary | (extended) | — | — |

The generic `GET /scenes` list without a project filter remains but is not used by the UI.

## Frontend

- `apps/web/src/app/projects/[id]/script/page.tsx` (NEW): act-by-act view with word budget bars, validation report (hard failures vs warnings, overlap metric labelled "quality metric"), editor (plain textarea per act in MVP) saving as new versions, version list with provider/model/prompt_version, approve button disabled while hard failures exist, "Generate / regenerate".
- `apps/web/src/app/projects/[id]/storyboard/page.tsx` (NEW): scene list (sequence, narration, visual intent, characters/locations, camera, shots, image prompt), per-scene edit form (validated server-side), version history drawer, reorder (up/down buttons first; drag-and-drop is optional later), insert/delete, divergence badges, **Approve storyboard** with a cost note ("Approving unlocks image and voice generation").
- MODIFY `stage-nav.tsx` to show Script/Storyboard states and stale reasons. Reuse P4's run-polling hook. Studio unification is P9.

## Services/Workflows

| Workflow | Trigger | Persisted | Retry/idempotency | Gate |
| --- | --- | --- | --- | --- |
| `script.generate` (+ inline `script.validate`) | POST | `ScriptVersion` n+1, per-act `llm_calls` | per-act cache; resumes after failure at the failed act | requires approved architecture; output unapproved (G2) |
| `storyboard.generate` | POST | `Scene` rows, `SceneVersion` v1, provenance | cached model call; deterministic span/slicing re-derivation is idempotent | requires approved script; output unapproved (G3) |
| `script.validate` | on save/approve, or POST | report inside `content.validation` | pure function | — |

## AI

- **Tasks:** `script` (strong model, per-act; the one place where model quality matters most), `script_repair` (same or cheaper), `storyboard` (medium-strong; structured JSON, sentence-span output). Models via settings (`script_llm_model` etc.) and the P2 routing table — nothing hard-coded. Prompts NEW in `packages/prompts/script_act/v1.md`, `script_repair/v1.md`, `storyboard/v1.md`.
- **AI decides:** wording and rhythm of the script, hook craft, which sentences group into a scene, visual intent/action/emotion, shot plan and camera choice, image-prompt drafts, which shots reuse an image.
- **Deterministic code decides:** act word budgets, tolerance checks, sentence ids and spans, narration slicing, scene ids/sequence/`scene_id`, `duration=None`, versions, approval, coverage check, hashes, staleness, banned-pattern and metric computation, reading-time estimate.
- **Validation:** Pydantic → validators → repair (≤2) → fail. The storyboard coverage check is a hard failure, so scenes can never silently drop or duplicate script text.
- **Originality:** the prompt demands new structure/framing; the n-gram overlap metric is an engineering quality signal surfaced to the user; thresholds are Decision pending; embedding-based similarity is P12; no legal assurance is given.
- **Cost:** script = the largest token spend in the pipeline, so it runs only after G1b and is cached per act; storyboard once per approved script version.

## Storage/media

No binary assets. Script/scene content is JSONB. Prompts are text files in `packages/prompts`. Image prompts are drafts only (generation is P6).

## Testing

- **Unit:** sentence splitter goldens; budget math (tolerance edges); each validator; span coverage (gaps, overlaps, out-of-order, duplicate); narration slicing equality; `SceneSpec` v1/v2 parse compatibility; hash determinism and policy cases (shared with the versioning doc tests).
- **Database:** partial unique indexes; `(scene_id, version)` uniqueness; soft delete leaves versions; `upgrade/downgrade`.
- **API:** all routes incl. 409s, stale `base_version`, reorder permutation validation, approve with divergences.
- **Workflow (fake provider + recorded fixtures):** per-act generation resumes after an injected failure at act 3 without re-calling acts 1–2; second identical run = 0 calls; invalid span assignment repaired once, then fails cleanly; storyboard approval blocked by hard failures; editing a scene after G3 un-approves only that scene; new script version marks the storyboard stale-suggested while unchanged-span scenes are reported preserved.
- **Frontend/E2E:** script edit → save → approve; storyboard generate (fake provider) → edit scene → reorder → approve; blocked states visible. Playwright runs with `PLAYWRIGHT_CHROMIUM_PATH` on this OS.
- **Not claimed:** live-model quality; the 10–15 minute target is verified only against the *word-count estimate*, real length is P7.

## Observability

Per-act and per-call logs (`workflow_id`, `project_id`, `script_id`, `scene_id`, `provider`, `model`, `duration`, `status`, `error`); validation reports persisted; `llm_calls` rollup per project visible in the UI; counters of repair attempts per act (a high rate signals a prompt problem). Token fields depend on KI-2.

## Failure handling & idempotency

Script persists per act; storyboard persists atomically (all scenes or none — one transaction around creation after validation). Retries resume via cache. Optimistic concurrency on every edit (`base_version`). Soft deletes; reorder is a transaction. A storyboard run that fails validation leaves the previous storyboard untouched. Keys: `(script_id, version)` and `(scene_id, version)` unique constraints already exist; run keys per API table; see [retry table](../docs/workflows/retry-and-recovery.md#idempotency-keys).

## Acceptance criteria (Checkpoint E)

1. `POST …/script/generate` without an approved architecture → 409; with one (fake provider) → a `ScriptVersion` whose total words are within tolerance of the computed budget and whose acts follow the architecture order; second identical run → 0 provider calls.
2. A failure injected at act N leaves acts <N persisted; retry completes without re-calling them.
3. Validation report distinguishes hard failures from warnings; metrics include `source_overlap_ratio`, `longest_verbatim_run`, `reading_time_seconds_estimate` (labelled estimates/quality metrics); approve is refused while hard failures exist.
4. Editing the script creates v2; v1 remains readable; approving v2 flips `approval_current` atomically; with an existing storyboard the API demands `acknowledge_downstream` and the storyboard reports `stale` with reason `script_changed`.
5. `storyboard.generate` creates scenes whose spans cover every script sentence exactly once; every `SceneVersion.data` validates as `SceneSpec` v2 with `duration=None`; scene ids/sequence derive from rows.
6. Editing a scene creates v+1 (v1 retained); reorder changes only `sequence`; delete is soft; insert works at any position.
7. `POST …/storyboard/approve` fails with hard failures or incomplete coverage; on success every active scene's current version is `approval_current`; editing one scene afterwards un-approves only it and G3 reports unsatisfied.
8. `require_approved(project,'storyboard')` is the single check used by later expensive workflows (test with a dummy workflow).
9. Staleness is computed, never stored: deleting/recomputing needs no cascade writes (test: change script text → stage summary changes; no row updates other than the new version).
10. `make lint`, `make test` with DB, migrations reversible, E2E passes.

## Deliverables

Versioning primitives; migration; sentence segmentation; script schema + generation + validators + edit/approve; `SceneSpec` v2 + `SceneDraft` + `ShotSpec`; storyboard generation and scene service; gates G2/G3; routes; script and storyboard pages; fixtures; prompts at `v1`.

## Dependencies

Depends on P4 (approved architecture), P2, and the primitives in [`versioning-and-invalidation.md`](versioning-and-invalidation.md). **Blocks** P6, P7 (both need an approved storyboard and scene versions), P8 (scene order/spans/camera).

## Docs to update at phase end

[`status.md`](../docs/reference/status.md), [`script-generation.md`](../docs/domains/script-generation.md), [`storyboard-system.md`](../docs/domains/storyboard-system.md) (identifier decision recorded; shot representation), [`scene-data-model.md`](../docs/data/scene-data-model.md), [`project-system.md`](../docs/domains/project-system.md) (gate state), [`workflow-overview.md`](../docs/workflows/workflow-overview.md) (invalidation model: hash-based chosen), API docs, changelog.

## Do NOT

Do not let the model write `narration` for a scene or output ids, sequence, durations or approval; do not mutate an existing `ScriptVersion`/`SceneVersion`; do not make the 2–7 s clamp or 2.5 words/s a hard rule — they are estimates; do not change `Timeline`/Remotion in this phase; do not resolve characters against the DB here (P6); do not generate images, voice or prompts for real providers; do not add a `shots` table without a P6 need; do not cascade-write staleness; do not claim overlap numbers prove originality.

## Decision points

- **D-P5-1** One `Script` per project (recommended; `UNIQUE(project_id)`) vs several alternative scripts per project.
- **D-P5-2** Shots inside `SceneVersion.data` (recommended) vs a `shots` table.
- **D-P5-3** Narration = sliced script spans, with `narration_override` as an explicit divergence (recommended) vs free-form scene narration.
- **D-P5-4** Tolerances (±15% per act, scene-count range, overlap thresholds) start as configuration constants; calibrate on real runs.
- **D-P5-5** Drag-and-drop reorder deferred to P9; up/down buttons suffice for the MVP.
- **Disagreement flag:** the contract's D4 names `artifacts.approved_at` only; this plan extends the same fields to `script_versions`/`scene_versions` because those tables already own the versions. If P2 prefers modelling scripts/scenes as artifacts, P5-T2 collapses into that — decide before P4 starts.
