# Scenes API

> CRUD for `scenes` — the per-scene identity and status used for granular regeneration.

## Status

**Partially implemented.** Scene rows have CRUD. The scene *content* (`SceneSpec` in `scene_versions.data`) has **no endpoint**, and nothing generates or regenerates scenes (**Planned — not implemented**: [storyboard-system](../../domains/storyboard-system.md)).

Base: `/api/v1/scenes`

## Create — `POST /scenes` → 201
`project_id` (required; unknown → 409), `sequence` (int ≥ 1, required), optional `script_id`. Server sets `status=draft`. `sequence` is not unique per project.

## Read model
`id, created_at, updated_at, project_id, script_id, sequence, status, error`.

## Update — `PATCH /scenes/{id}`
Allowed: `sequence` (≥1), `status` (`draft|ready|generating|failed`).

## Other
List/get/delete; deleting removes versions and leaves assets (`scene_id` → NULL).

Related: [scene-data-model](../../data/scene-data-model.md) · [workflows/storyboard-workflow](../../workflows/storyboard-workflow.md)

Example response (`201`):
```json
{"id":"e4d2…","created_at":"…","updated_at":"…","project_id":"fae5…","script_id":null,"sequence":1,"status":"draft","error":null}
```
`scenes.id` is a UUID; `sequence` is the ordering key; `SceneSpec.scene_id` (a string) lives inside `scene_versions.data` and is not exposed or validated here — see the [identifier mapping](../../domains/storyboard-system.md).
