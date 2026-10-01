# Asset Data Model

> Generic record for every generated or imported media file, and the render record that consumes them.

## Status

**Partially implemented.** `assets` and `renders` tables and CRUD API exist. The `Storage` layer can write files, but no code creates an asset row from a file or updates `storage_key`/`checksum` — through the API these fields are read-only (not in create/update schemas).

## Asset

| Field | Notes |
| --- | --- |
| `project_id` | required, cascade |
| `scene_id` | optional, SET NULL when the scene is deleted |
| `type` | `image, audio, voice, music, sfx, video, thumbnail, subtitle, reference, render` |
| `status` | `pending → generating → ready | failed` |
| `storage_key` | relative key under the storage root (never an absolute path) |
| `mime_type`, `size_bytes`, `checksum` | checksum = sha256 hex; `LocalStorage.put` returns `(size, sha256)` |
| `error` | persisted failure for retry |
| `metadata` JSONB | provider, model, prompt, seed, dimensions, duration… (convention *Decision pending*) |

Binary content is never in PostgreSQL ([storage-layout](storage-layout.md)).

## Regeneration

Granular regeneration is the design driver: each asset has its own id/status/error so "regenerate scene 32's image" creates or replaces one asset row only. Whether regeneration creates a new row (history) or overwrites is *Decision pending*; versions of assets are not modelled.

## Render

`Render(project_id, status queued|rendering|completed|failed, timeline JSONB, output_asset_id?, started_at, finished_at, error)`. `timeline` snapshots the exact `Timeline` JSON used, so a render is reproducible; the MP4 is an `Asset(type=render)` referenced by `output_asset_id`. **No render workflow exists**; the only render that works is the CLI sample (`make render-sample`), which writes outside this table ([media/rendering](../media/rendering.md)).

## Reference assets

Character/location reference images are `type=reference` with no explicit link to characters (Planned — not implemented). See [media/image-consistency](../media/image-consistency.md).

## Related

[api/resources/assets](../api/resources/assets.md) · [domains/image-generation](../domains/image-generation.md) · [data-lifecycle](data-lifecycle.md)

## Artifact versions and dependencies (target)

**Status: Planned — not implemented; every option is Decision pending.** Semantics (what "stale", "preserve" and "invalidate" mean, and the dependency graph) are defined once in [workflows/workflow-overview](../workflows/workflow-overview.md). This section is only the data direction.

**Today.** Versioned artifacts: `script_versions`, `scene_versions`. Everything else is unversioned; an image for scene 12 "v2" would simply be another `assets` row with no version number, no `current` marker and no link to what produced it. Nothing records what an artifact was derived from beyond `prompt_version/provider/model` on script versions. Changing a script, character or Visual Bible therefore cannot mark downstream scenes/images stale. There is also no cache key for reusing an identical earlier generation ([ai/ai-cost-strategy](../ai/ai-cost-strategy.md)).

| Option | Shape | Trade-off |
| --- | --- | --- |
| 1. Columns on `assets` | `version`, `supersedes_id` (self FK), `is_current`, `input_hash`, `stale` | Simplest; covers asset history and a cache key; does not cover non-asset artifacts (scripts, candidates) |
| 2. Dependency edge table | `artifact_dependencies(artifact_type, artifact_id, depends_on_type, depends_on_id, depends_on_version)` | Expresses the full graph and enables "what is affected if X changes?" queries; polymorphic references have no FK integrity |
| 3. Hash-based staleness | each artifact stores an `input_hash` of its inputs' ids+versions; stale = recomputed hash differs | No edge table; cheap to evaluate; cannot answer "who depends on X?" without scanning |

Options combine well (1 or 3 for assets, 2 for the graph). The Visual Bible, characters and the approved story are the typical upstream artifacts. Whether regeneration keeps history (new row) or overwrites is also open.

## Gaps vs. target

Thumbnails are just `type=thumbnail` rows with no link to their source, and `assets.project_id` is NOT NULL, so a library-level (project-less) thumbnail is impossible ([KI-23](../reference/status.md#known-issues-and-limitations)). Shot-level assets: [scene-data-model](scene-data-model.md#scene-shot-prompt-and-asset-are-different-things-target). No file-serving route and no route that writes files ([KI-9](../reference/status.md#known-issues-and-limitations), [KI-17](../reference/status.md#known-issues-and-limitations)).
