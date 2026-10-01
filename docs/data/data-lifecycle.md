# Data Lifecycle

> How records are created, change state, are versioned and deleted.

## Status

**Partially implemented.** Create/update/delete exist via the generic CRUD API and database cascades. Automated lifecycle (state transitions, cleanup, retention) is **Planned — not implemented**.

## Creation

Today only via `POST /api/v1/<resource>`; nothing creates rows automatically. Target: ingestion/generation workflows create entities and drive statuses ([workflows/workflow-overview](../workflows/workflow-overview.md)).

## State

Statuses are plain columns; the API lets a client PATCH any valid value (no transition guard). Target lifecycles: source `discovered→importing→imported|failed`; transcript `pending→processing→ready|failed`; asset `pending→generating→ready|failed`; render `queued→rendering→completed|failed`. Failures should write `status=failed` + `error` and be retryable ([workflows/retry-and-recovery](../workflows/retry-and-recovery.md)).

## Versioning

Scripts and scenes get new rows in `*_versions` (never edited in place by convention). Transcripts have a `transcripts.version` column, but versioning is a **target**: the API cannot set `version` (default 1), so a second transcript for the same video collides on `(source_video_id, 1)` and returns 409 ([KI-13](../reference/status.md#known-issues-and-limitations)). Immutability of `*_versions` rows is a convention — no constraint or API enforces it. Assets and characters are unversioned.

## Deletion (hard, cascading)

| Deleting | Effect |
| --- | --- |
| channel | videos kept, `channel_id` → NULL |
| source_video | transcripts, chunks, collection and project links deleted |
| project | scripts(+versions), scenes(+versions), characters, locations, assets, renders, project_sources deleted |
| script | scenes kept, `script_id` → NULL |
| scene | scene_versions deleted; assets kept, `scene_id` → NULL |
| asset | renders kept, `output_asset_id` → NULL |

**Files are not deleted** when rows are (and nothing in the API creates files today — [KI-9](../reference/status.md#known-issues-and-limitations)): deleting an asset row leaves its file in `data/` (orphan). Orphan cleanup: Planned — not implemented ([storage-layout](storage-layout.md)).

## Retention, backup

No retention policy or soft delete. Backups are manual (`pg_dump` + copy `data/`): [operations/backups](../operations/backups.md), [recovery](../operations/recovery.md).

## Regeneration

Intended to replace/add only the affected scene/asset. Overwrite vs. history: *Decision pending* ([asset-data-model](asset-data-model.md)).

## Related

[data-model](data-model.md) · [entity-relationships](entity-relationships.md)

## Derived data and invalidation (Planned — not implemented)

No dependency tracking exists, so changing an upstream artifact (script, character, visual style) does not mark downstream scenes/assets stale; callers must regenerate manually. Analysis-result caching is also absent. Both are prerequisites for cheap, granular regeneration. Semantics: [workflows/workflow-overview](../workflows/workflow-overview.md); data direction: [asset-data-model](asset-data-model.md#artifact-versions-and-dependencies-target); other story-side gaps: [story-data-model](story-data-model.md#target-model-gaps-verified-absent-from-the-schema).
