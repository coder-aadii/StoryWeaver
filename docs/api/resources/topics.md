# Topics API

> CRUD for `topics` (labels for themes found across sources).

## Status

**Implemented** as plain CRUD. Automatic topic extraction/classification and linking topics to videos/chunks are **Planned — not implemented** (no link table exists).

Base: `/api/v1/topics`

## Create — `POST /topics` → 201
`name` (1–255, unique), `slug` (1–255, unique, pattern `^[a-z0-9]+(?:-[a-z0-9]+)*$`), optional `description`. Duplicate name/slug → 409; bad slug → 422.

## Read model
`id, created_at, updated_at, name, slug, description`.

## Update — `PATCH /topics/{id}`
Allowed: `name`, `description` (slug is immutable).

## Other
List/get/delete standard.

Related: [topic-and-collection-system](../../domains/topic-and-collection-system.md) · [source-data-model](../../data/source-data-model.md#organisation)

Example response (`201`):
```json
{"id":"91ab…","created_at":"…","updated_at":"…","name":"Prehistoric survival","slug":"prehistoric-survival","description":null}
```
