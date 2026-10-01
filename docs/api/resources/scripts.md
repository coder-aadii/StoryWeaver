# Scripts API

> CRUD for `scripts` (named script slots within a project).

## Status

**Partially implemented.** Script rows have CRUD. **Script versions have no endpoint**, and no generation exists (**Planned — not implemented**: [script-generation](../../domains/script-generation.md)).

Base: `/api/v1/scripts`

## Create — `POST /scripts` → 201
`project_id` (required; unknown → 409), `title` (1–512).

## Read model
`id, created_at, updated_at, project_id, title`.

## Update — `PATCH /scripts/{id}`
Allowed: `title`.

## Other
List/get/delete. Deleting a script keeps its scenes (`script_id` → NULL) and deletes its versions. There is no `?project_id=` filter ([pagination](../pagination.md)).

Related: [story-data-model](../../data/story-data-model.md)

Example response (`201`):
```json
{"id":"a7b1…","created_at":"…","updated_at":"…","project_id":"fae5…","title":"Main script"}
```
