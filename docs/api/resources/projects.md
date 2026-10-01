# Projects API

> CRUD for `projects`, the unit that turns sources into a video.

## Status

**Implemented** as plain CRUD (used by the web Projects pages). Pipeline actions (analyze, script, storyboard, render) and `project_sources` linking are **Planned — not implemented**.

Base: `/api/v1/projects`

## Create — `POST /projects` → 201
`title` (1–512, required), optional `description`, `settings` (free-form object, default `{}`). Server sets `status=draft`.

## Read model
`id, created_at, updated_at, title, description, status, settings, error`.

## Update — `PATCH /projects/{id}`
Allowed: `title`, `description`, `status` (`draft|analyzing|scripting|storyboarding|generating|rendering|qa|completed|failed`), `settings`. No transition validation. `settings` PATCH replaces the whole object.

## Other
List/get/delete. **Delete cascades** to scripts, scenes, characters, locations, assets and renders ([data-lifecycle](../../data/data-lifecycle.md)); files under `data/` are left behind.

```bash
curl -s -X PATCH localhost:8000/api/v1/projects/$ID -H 'content-type: application/json' -d '{"status":"scripting"}'
```

Related: [project-system](../../domains/project-system.md) · [project-data-model](../../data/project-data-model.md)

Example response (`201`):
```json
{"id":"fae5…","created_at":"…","updated_at":"…","title":"Ice Age","description":null,"status":"draft","settings":{},"error":null}
```
`PATCH` with `{"settings": null}` is accepted by the schema but violates NOT NULL → 409 ([errors](../errors.md#known-quirks-code-level-documented-as-is)). The approval-gate state for candidates/storyboards has no defined home yet (*Decision pending*: [domains/project-system](../../domains/project-system.md)); `project_sources` has no endpoint.
