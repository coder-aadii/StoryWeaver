# Versioning and Invalidation — Implementation Design

> The concrete, buildable mechanism for artifact versions, "current" pointers, approvals, and **computed** staleness used by P4–P9: how StoryWeaver knows what is out of date after an upstream change, without cascade writes or a graph engine.

## Status

Planned. Current state (verified): **Partially implemented — tables only.** `script_versions` and `scene_versions` exist with `UNIQUE (parent, version)` and no API; `transcripts.version` exists (KI-13: API cannot set it); `assets` has no version, hash or "current" notion; `renders.timeline` stores a JSONB snapshot; nothing computes or stores staleness, no dependency edges exist ([KI-22](../docs/reference/status.md#known-issues-and-limitations)). The *conceptual* model is already specified in [workflow overview](../docs/workflows/workflow-overview.md#artifact-dependency-and-invalidation-model--target-decision-pending) (options A/B/C) and the [asset data model](../docs/data/asset-data-model.md); this document **chooses and specifies** it and adds nothing to the product vision.

Part of [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md); first used in P4–P5 ([`04-story-script-storyboard.md`](04-story-script-storyboard.md)), extended by P6 (assets), P8 (timeline/render/QA), P9 (UI).

## Design decision (summary)

| Question | Decision |
| --- | --- |
| How is staleness known? | **Computed at read time** by comparing an artifact's recorded `input_hash` with the hash of its *current* declared upstream inputs. Nothing is written when an upstream changes. (Docs option A, hash-in-record.) |
| Are edges needed? | Only for **display and lineage** (`artifact_dependencies`, FK columns such as `scene_versions.script_version_id`). Correctness never depends on them. (Options B/C used as annotations.) |
| What happens to stale things? | Nothing automatic. They stay usable; the user chooses **regenerate** or **keep**. Costly assets are never regenerated implicitly. |
| Are versions mutable? | Never. Edits and regenerations create version `n+1`; old versions stay readable. |

## Version rules per artifact type

| Artifact | Storage | Identity of a version | "Current" | Created by | Approval |
| --- | --- | --- | --- | --- | --- |
| Transcript | `transcripts` | `(source_video_id, version)` | highest `version` with `is_current` (P1) | `source.fetch_transcript` service (not the API payload) | n/a |
| `source_analysis`, `narrative_opportunity_set` | `artifacts` | `(lineage_id, version)` | highest version of the lineage | workflow or user edit | optional |
| `story_candidate`, `story_architecture` | `artifacts` | `(lineage_id, version)` | highest version; **approved** = `status='approved'` | workflow / user edit | **required** (G1, G1b) |
| `visual_bible` | `artifacts` | `(lineage_id, version)` | highest version | P6 workflow / edit | with G3 (storyboard) or its own accept (P6 decision) |
| Script | `script_versions` | `(script_id, version)` | highest `version` | `script.generate` / edit | **required** (G2): `approval_current` |
| Scene | `scene_versions` | `(scene_id, version)` | highest `version` of the scene | `storyboard.generate` / edit | **required** (G3): `approval_current` per scene |
| Image / voice / subtitle asset | `assets` (P6/P7 columns) | `(scene_id, type, version)` | `is_current` (partial unique per scene+type) | `scene.image`, `scene.voice`, `subtitles.build` | none (accepted implicitly by using it; user may *pin*) |
| Timeline | **not stored as an artifact** | `timeline_hash` | rebuilt on demand | `timeline.build` (pure function) | n/a |
| Render | `renders` | `renders.id` (+ `timeline_hash`, P8) | newest `completed` | `render.project` | n/a |
| QA report | `artifacts` kind `qa_report` | `(render_id)` | newest for the render | `qa.run` | n/a |

Rules:

1. **Immutability.** No UPDATE of a version's content. Permitted updates: lifecycle fields (`status`, `approval_*`, `is_current`, `error`, `kept_input_hash`).
2. **Monotonic versions.** `n+1` is assigned inside the creating transaction (`SELECT max(version) … FOR UPDATE` on the parent row, or retry on unique violation).
3. **Optimistic concurrency.** Every edit call carries `base_version`; if it is not the current version the API returns `409 conflict` (the client must refetch). Prevents lost updates between Studio tabs.
4. **Failed generations create no version.** A version row exists only for a successfully validated output; failures live on `workflow_runs.error` (so "current" never points at garbage).
5. **Soft deletion.** Scenes use `deleted_at`; versions and assets of a deleted scene remain.

## Approval and gates

Gates are **persisted facts**, checked by one helper (`require_approved(db, project_id, kind)`; P4-T5) that asserts *an approved version exists and equals the current version of that lineage*.

| Gate | Object | Stored as |
| --- | --- | --- |
| G1 candidate chosen | `story_candidate` artifact | `status='approved'`, `approved_at`, `approved_by` (`user` or `auto:<rule>`) |
| G1b architecture accepted | `story_architecture` artifact | same |
| G2 script accepted | `script_versions` row | `approved_at`, `approved_by`, `approval_current` |
| G3 storyboard accepted | every active scene's current `scene_versions` row | same; satisfied iff **all** active scenes' highest versions are `approval_current` |

- Approving version *n* clears `approval_current` on the previously approved version in the same transaction (partial unique indexes enforce one-current-approval). The history (`approved_at`/`approved_by` of earlier versions) is kept.
- Editing an approved object creates an unapproved `n+1`; the gate reads as unsatisfied until re-approved. Because staleness is hash-based, downstream artifacts built from *n* show `stale` rather than vanishing.
- Re-approving a **different** object while downstream artifacts exist returns `409 downstream_exists` with a summary; the client resubmits with `acknowledge_downstream=true`. Nothing is deleted.
- Automatic selection is possible only for G1 via the explicit project setting (default off) and is recorded as `approved_by='auto:…'`. It does not exist for G2/G3.

## `input_hash` and `generation_key`

Two hashes with different jobs (this resolves the contract's D2 cache key and the staleness need):

| Hash | Purpose | Content | Recorded on |
| --- | --- | --- | --- |
| **`input_hash`** | Staleness: "has what this was built from changed?" | Canonical hash of the **content** of exactly the upstream inputs the artifact *declares* (see below). **Excludes** provider, model, prompt version and seed — switching models must not make accepted work look stale | each versioned row (`artifacts`, `script_versions`, `scene_versions`, `assets`, `renders` as `timeline_hash`) |
| **`generation_key`** | Idempotency / cache: "have we already produced this exact output?" | `hash(input_hash, task, prompt_name, prompt_version, provider, model, generation params, seed)` | `llm_calls` (as the cache key with `task`/`model`/`prompt_version`/`input_hash` columns per D2) and `workflow_runs.idempotency_key` |

For **deterministic** outputs (timeline, subtitle track, stage summary) there is no `generation_key`; the `input_hash` of content is the whole story, plus a `code_version` constant (e.g. `TIMELINE_BUILDER_VERSION`) mixed in so a code change that alters output invalidates correctly.

### What each consumer declares as input

| Consumer | Declared inputs (hashed as content) | Explicitly **not** inputs |
| --- | --- | --- |
| `source_analysis` | current transcript text hash + `normalizer_version` | project settings |
| `narrative_opportunity_set` | `source_analysis` content hash | — |
| `story_candidate` | opportunity-set hash, guidance string, count | — |
| `story_architecture` | approved candidate content hash (as edited), `target_minutes`, genre | other candidates |
| Script version | architecture content hash, `target_minutes`, tone, language | candidates |
| Scene version (storyboard) | script version content hash **and** that scene's `script_span.span_hash` | other scenes' content, images |
| Image asset | scene's `image_prompt`, `negative_prompt`, `camera.shot`, referenced character/location **definitions** (their content hashes), `visual_bible` content hash, image params (size, style id) | narration text, voice, subtitles |
| Voice asset | normalised narration text, voice id, speech params | image prompt |
| Subtitle track | subtitle/narration text, measured audio duration (voice asset checksum), subtitle style version | image |
| Timeline (derived) | ordered list of per-scene `(scene_id, image checksum, audio checksum + measured duration, camera, subtitle track hash)` + `Timeline` schema version + `TIMELINE_BUILDER_VERSION` + fps/resolution | prompts, text of unused fields |
| Render | `timeline_hash` + composition version | QA |
| QA report | render checksum + QA ruleset version | — |

An input list is **code, not data**: one function per consumer (`inputs_for(kind, owner) -> dict`) in `apps/api/app/projects/dependencies.py` (NEW). Adding an input that influences output without declaring it is a bug; tests enumerate declarations against fixtures.

### Canonicalisation

JSON with sorted keys, no whitespace, UTF-8, strings Unicode-NFC-normalised and stripped of trailing whitespace, floats rounded to 6 decimals, `None` kept (distinct from missing), volatile fields (`id`, timestamps, `error`, `status`) excluded, a leading `{"v": <canonicalisation version>}`. SHA-256, hex. Binary assets contribute their stored `checksum` (SHA-256 already a column).

## Policy table

Default behaviour when an upstream changes. "Stale-suggested" = the stage summary reports `stale` with a reason; nothing is regenerated or deleted.

| Change | Script | Storyboard | Per-scene image | Per-scene voice | Subtitles | Timeline | Render |
| --- | --- | --- | --- | --- | --- | --- | --- |
| New candidate approved | stale | stale | stale (via script/scenes) | stale | stale | rebuild on demand | stale |
| Architecture edited (new version) | stale | stale-suggested | preserved until scenes change | preserved until scenes change | preserved | — | — |
| New script version | — | stale-suggested **as a set**; scenes whose span text still exists contiguously report **preserved** | preserved if scene unchanged | preserved if scene unchanged | preserved | rebuilt | stale if hash differs |
| Scene narration changed (new scene version) | — | that scene `fresh` (it is the edit) | **preserved** (narration not an image input) | **stale** | **stale** | rebuilt | stale |
| Scene `image_prompt`/`negative_prompt`/`camera.shot` changed | — | — | **stale** | preserved | preserved | rebuilt | stale |
| Scene camera *movement* changed | — | — | preserved (not an image input) | preserved | preserved | rebuilt | stale |
| Character/location definition or visual bible changed | — | scenes referencing it: stale-suggested | **only scenes that reference it: stale** | preserved | preserved | rebuilt | stale |
| New image/voice version created | — | — | — | — | voice → subtitles stale | rebuilt | stale |
| Timeline hash unchanged after any of the above | — | — | — | — | — | identical | **fresh (reused)** |
| Render completed | — | — | — | — | — | — | QA report stale |
| Provider/model/prompt version changed | **nothing becomes stale** (not an input); a regenerate under the new setting is a new `generation_key` | | | | | | |

**Unchanged hash ⇒ preserved.** The "timeline is always rebuilt on demand" rule is cheap because `timeline.build` is a pure function: staleness is irrelevant for it, only the *render* compares `timeline_hash`.

### Invalidate vs preserve (user choice)

For any `stale` object the Studio offers:
- **Regenerate** → new version (`n+1`), new `input_hash`, old version kept.
- **Keep** → writes `kept_input_hash = current upstream hash` on the object. State computation treats it as fresh while the upstream hash equals `kept_input_hash`; a *further* upstream change makes it stale again. (No data duplicated; fully reversible by clearing the column.)
- **Regenerate all stale** → batch, subject to a dry-run cost preview (below) and explicit confirmation when estimated paid calls > a configurable threshold.

## Regeneration scopes

| Scope | Smallest unit | Workflow kind | Notes |
| --- | --- | --- | --- |
| `source_analysis` | one source (project-independent) | `source.analyze` | cache hit if transcript hash unchanged |
| `candidate` | candidate set or one lineage | `story.candidates` | keeps older proposals unless "replace" |
| `architecture` | one | `story.architecture` | requires G1 |
| `script` | whole script, or **one act** | `script.generate` (act subset) | per-act persistence makes act-level regen natural; produces a new script version |
| `scene` | one scene | `storyboard.generate` (scene subset) | new `SceneVersion`; neighbours untouched |
| `image` | one scene's image | `scene.image` | never implicit |
| `voice` | one scene's narration audio | `scene.voice` | never implicit |
| `subtitles` | one track / all | `subtitles.build` | deterministic, free |
| `timeline` | project | `timeline.build` | deterministic, free |
| `render` | project | `render.project` | new `renders` row |

**Dry run first:** `POST /api/v1/projects/{id}/regenerate` accepts `{scope, target_id?, mode: "stale_only"|"explicit", dry_run: true}` and returns the plan `{workflow_kind, targets[], estimated_provider_calls, estimated_paid: bool, preserved[]}` computed from `compute_state`; the same call with `dry_run=false` starts the runs (`202 {run_ids}`) and refuses (`409 gate_not_satisfied`) if a prerequisite gate is open (e.g. image regeneration before G3).

## Stage summary API

`GET /api/v1/projects/{id}/stages` (NEW; implemented incrementally in `apps/api/app/projects/stages.py`, P4-T10 onward). Pure read; no auth (localhost).

Response concept:

```json
{
  "stages": [
    {"stage": "story", "state": "stale", "current_version": 3, "approved_version": 2,
     "stale_reason": "upstream_changed", "blocking_gate": null,
     "counts": null, "active_run": null},
    {"stage": "visuals", "state": "fresh", "counts": {"fresh": 18, "stale": 3, "missing": 0, "failed": 1, "running": 0},
     "blocking_gate": "G3", "active_run": "run-id"}
  ]
}
```

- `stage` ∈ `source, research, story, script, storyboard, visuals, audio, timeline, qa, render` (the Studio's ten stages).
- `state` ∈ `missing | fresh | stale | running | failed` (`blocked` is not a state: a closed gate is reported in `blocking_gate`, and the state is `missing`).
- `stale_reason` ∈ `upstream_changed | script_changed | prompt_changed | narration_changed | definition_changed | timeline_changed | ruleset_changed` (stable codes for UI text).
- Per-scene stages (`storyboard`, `visuals`, `audio`) carry `counts`; `GET /api/v1/projects/{id}/scenes/status` returns the per-scene breakdown with each scene's per-stage state for the Studio grid.
- Roll-up: `failed` if any child failed and none running; else `running` if any running; else `stale` if any stale; else `missing` if any missing; else `fresh`.
- Errors: 404 unknown project. Idempotent and cheap (hash comparisons over rows already in the DB; target < 100 ms for ≤ 200 scenes — measure in P10).

## Algorithms

```python
def canonical_json(obj) -> bytes: ...          # rules above; pure, no I/O
def content_hash(obj) -> str:                  # sha256 hex of canonical_json
    return sha256(canonical_json(obj)).hexdigest()

def generation_key(input_hash, *, task, prompt_name, prompt_version,
                   provider, model, params, seed) -> str:
    return content_hash({"i": input_hash, "t": task, "p": [prompt_name, prompt_version],
                         "m": [provider, model], "k": params, "s": seed})

def current_input_hash(kind, owner) -> str:    # the ONLY place declared inputs live
    return content_hash(inputs_for(kind, owner))   # dependencies.py, one function per kind

def compute_state(rec, run=None) -> State:
    if run and run.status in {"queued", "running"}:   return State("running")
    if rec is None:                                   return State("missing")
    if rec.failed_latest:                             return State("failed")   # from the newest failed run, if no newer version
    cur = current_input_hash(rec.kind, rec.owner)
    if cur == rec.input_hash or cur == rec.kept_input_hash:
        return State("fresh", version=rec.version)
    return State("stale", version=rec.version, reason=reason_for(rec.kind, rec, cur))

def reason_for(kind, rec, cur) -> str:
    # compare per-field sub-hashes stored in rec.input_parts (dict of name -> hash),
    # e.g. {"narration": h1, "voice": h2}; the differing key maps to a reason code.
```

`input_parts` (a small JSONB of per-input sub-hashes stored alongside `input_hash`) is what lets the policy table distinguish "narration changed" from "image prompt changed" without storing old content. Stored on `artifacts`, `scene_versions`, `assets`, `renders` (as `timeline_parts`).

Save path (pseudocode, one transaction):

```python
def create_version(parent, payload, *, base_version, derived_from):
    lock(parent)
    if parent.current_version != base_version: raise Conflict
    validate(payload)                                   # Pydantic + validators
    parts = {name: content_hash(v) for name, v in declared_inputs(parent.kind, derived_from).items()}
    row = insert(version=parent.current_version + 1, data=payload,
                 input_hash=content_hash(parts), input_parts=parts, ...)
    record_edges(row, derived_from)                     # display only
    return row
```

Approval path: `approve(row)` clears `approval_current` on siblings, sets it on `row`, returns downstream summary if any dependent exists (computed by *querying objects whose recorded parts reference this lineage*, via the edge table — display only).

Storyboard span preservation (script changed): for each active scene compute `span_text_hash`; the new script's sentences are indexed by rolling-hash of contiguous sentence sequences; a scene is **preserved** if its exact sentence sequence occurs contiguously in the new version, and its new `script_span` is rebased (a new `SceneVersion` is created *only if the user accepts the rebase*; otherwise the scene is shown `stale` with reason `script_changed`). Pure function, unit-tested with insert/delete/reorder cases.

## Migrations per phase

| Phase | Change | Reversible |
| --- | --- | --- |
| P2 | `artifacts` incl. `input_hash`, `input_parts`, `kept_input_hash`, `lineage_id`, `approved_*`, `status`; `artifact_dependencies`; `llm_calls`; `workflow_runs` | yes |
| P4 | partial unique indexes for approved candidate/architecture (see [04](04-story-script-storyboard.md)) | yes |
| P5 | `script_versions` / `scene_versions`: `approved_*`, `approval_current`, `input_hash`, `input_parts`, `kept_input_hash`, provenance; `scenes.deleted_at`; `scripts UNIQUE(project_id)` | yes |
| P6 | `assets`: `version`, `is_current`, `scene_version_id` FK, `input_hash`, `input_parts`, `kept_input_hash`, partial unique `(scene_id, type) WHERE is_current` | yes |
| P7 | `assets` reused for voice/subtitle; add `measured_duration_seconds` (or in `metadata` — decide in P7) | yes |
| P8 | `renders.timeline_hash`, `renders.timeline_parts`, composition version; `qa_report` artifacts | yes |

Each revision is tested `upgrade → downgrade → upgrade` and `alembic check`.

## Tests

- **Determinism (property-style, no new dependency):** seeded random generation of nested JSON objects (key order shuffles, NFC/NFD variants, trailing whitespace, float representations like `1.0` vs `1.0000001`); assert `content_hash` equal for equivalent inputs and different for any real change. If the team prefers `hypothesis`, adding it is a **Decision pending** (new dev dependency).
- **Declaration coverage:** for each consumer kind, mutate each declared input in a fixture and assert `compute_state` flips to `stale` with the expected reason; mutate each *non*-input (provider, model, narration for images) and assert it stays `fresh`. This is the test that prevents silent over/under-invalidation.
- **Policy table as a test:** parametrised table-driven test reproducing every row above.
- **No cascade writes:** after changing a script, assert the only new rows are the new version; no existing row's `updated_at` changed (except explicit lifecycle fields).
- **Keep/pin:** keep → fresh; second upstream change → stale again; clearing pin → stale.
- **Concurrency:** two `create_version` calls with the same `base_version`: exactly one succeeds, the other gets 409.
- **API:** stage summary roll-up cases; regenerate dry-run output equals the later real run's targets; gate refusal (409).
- **Migrations:** partial unique indexes enforce one current approval / one current asset.
- **Frontend (P9):** stale badge text per `stale_reason`; keep/regenerate actions call the right endpoints.

## Observability and failure handling

- Log `version.created`, `gate.approved|revoked`, `regenerate.planned|started` with project/scene/artifact ids and the `stale_reason` codes (never content).
- `compute_state` is a pure function over rows: it cannot fail midway or leave partial state. If an input declaration function raises (a bug), the stage reports `failed` with `error='declaration_error'` rather than hiding staleness.
- Hash-version bump: changing canonicalisation or a consumer's declared inputs requires bumping the `v` prefix / consumer code version; all existing rows then read `stale` (conservative) and the user can **keep** them in bulk. A one-off backfill command may recompute `input_hash` for rows when a bump is purely cosmetic (**Decision pending**, avoid unless needed).

## Explicitly NOT built

- No cascade/trigger writes, no background invalidation job, no "stale" column that must be kept in sync.
- No general DAG/graph engine or topological scheduler: only the declared per-consumer inputs above; edges are annotations.
- No automatic regeneration of anything that costs money; no auto-merge of conflicting edits (optimistic-concurrency 409 only).
- No cross-project artifact sharing of versions in the MVP (`source_analysis` is cacheable across projects by `generation_key`, but versions belong to one lineage).
- No content-addressed blob store; binary assets keep path + checksum.
- No distributed locks; single-process runner, row locks inside transactions.

## Decision points

- **D-V-1** `input_parts` JSONB (recommended; supports precise stale reasons) vs hash-only (smaller rows, vaguer reasons).
- **D-V-2** Rebase of preserved storyboard scenes after a script change: offered as a user-accepted action (recommended) vs automatic.
- **D-V-3** Whether `visual_bible` has its own accept gate or is approved together with the storyboard (G3).
- **D-V-4** Property-testing library (stdlib seeded random vs `hypothesis`).
- **D-V-5** Whether the voice measured duration lives in a column or `Asset.metadata` (P7).

## Docs to update when each phase lands

[`workflow-overview.md`](../docs/workflows/workflow-overview.md#artifact-dependency-and-invalidation-model--target-decision-pending) (record the chosen option: hash-in-record with annotation edges), [`asset-data-model.md`](../docs/data/asset-data-model.md), [`retry-and-recovery.md`](../docs/workflows/retry-and-recovery.md) (idempotency table: `generation_key` components now have columns), [`studio.md`](../docs/frontend/studio.md), [`status.md`](../docs/reference/status.md) rows (versioning, dependency invalidation, per-scene regeneration).
