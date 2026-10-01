# API Conventions

> Rules every endpoint follows today, and rules intended for future custom endpoints.

## Status

**Implemented** for generic CRUD; custom-endpoint conventions are **Planned**.

## Implemented

- **Versioning**: path prefix `/api/v1`. A breaking change would add `/api/v2`.
- **JSON** request/response; `Content-Type: application/json`.
- **IDs**: UUIDs in the path (`/projects/{item_id}`); non-UUID → 422.
- **Timestamps**: ISO-8601 with offset (`2026-10-01T12:48:42+05:30`).
- **Enums** are lowercase strings (`"draft"`). Unknown value → 422.
- **Create** (`POST`) returns 201 and the full read model. **Patch** is partial: only sent fields change; unknown fields are rejected (`extra="forbid"` → 422). **Delete** returns 204 with no body.
- **Read models vs table**: responses include a subset of columns (e.g. no `metadata`, no JSONB `segments`). See each resource doc.
- **PATCH semantics**: partial update via `exclude_unset`; unknown fields → 422; an explicit `null` clears only nullable columns and is a 422 on NOT NULL fields; update schemas have length limits (previously KI-4, resolved in P0). Details: [errors](errors.md#behavior-of-patch).
- **Server-managed fields** (`id`, timestamps, `version`, `storage_key`, `checksum`, `size_bytes`) cannot be set via the API.
- **CORS**: allowed origins from `CORS_ORIGINS` (defaults `http://localhost:3000`, `http://localhost:3100`).
- **Secrets** never appear in responses ([provider-endpoints](provider-endpoints.md)).

## Constraints of the generic CRUD factory

`crud_router` (`apps/api/app/api/crud.py`) supports tables with a **single UUID `id` primary key and a `created_at` column** (used for ordering). Composite-key join tables (`collection_videos`, `project_sources`) cannot use it as-is and therefore have no endpoints. The factory offers list/get/create/patch/delete only: **no `PUT`, no filtering, no sorting options, no nested resources** (e.g. `/projects/{id}/scenes`). Exposed timestamps are `created_at` and `updated_at`; `started_at`/`finished_at` on `renders` are not exposed.

## Planned conventions (custom operations)

Long-running operations (import channel, generate script, render) should return quickly with a `workflow_id` and a resource whose `status`/`error` can be polled, mirroring `LocalRunner`'s workflow ids. Action-style sub-routes (e.g. `POST /scenes/{id}/regenerate`) and idempotency keys: *Decision pending*. Not implemented.

## Not implemented

Filtering/sorting params, `PUT`, nested routes, total counts ([pagination](pagination.md)), bulk endpoints, ETags/optimistic concurrency, rate limiting, request IDs.

Related: [errors](errors.md) · [architecture/backend-architecture](../architecture/backend-architecture.md)
