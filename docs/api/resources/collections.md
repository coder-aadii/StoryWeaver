# Collections API

> CRUD for `collections` — named groups of source videos (e.g. "History").

## Status

**Partially implemented.** Collection rows have CRUD. **Adding/removing videos has no endpoint** (the `collection_videos` table exists but is unreachable via the API).

Base: `/api/v1/collections`

## Create — `POST /collections` → 201
`name` (1–255, unique → 409 on duplicate), optional `description`.

## Read model
`id, created_at, updated_at, name, description`.

## Update — `PATCH /collections/{id}`
Allowed: `name`, `description`.

## Other
List/get/delete standard. Deleting removes membership rows, not the videos.

## Planned — not implemented
Membership endpoints (e.g. `PUT /collections/{id}/videos/{video_id}`), listing a collection's videos, "unused ideas in this collection" queries. Shape: *Decision pending*.

Related: [topic-and-collection-system](../../domains/topic-and-collection-system.md)

Example response (`201`):
```json
{"id":"5e0f…","created_at":"…","updated_at":"…","name":"History","description":null}
```
`collection_videos` has a composite primary key, so the generic factory cannot expose it ([API-conventions](../API-conventions.md#constraints-of-the-generic-crud-factory)).
