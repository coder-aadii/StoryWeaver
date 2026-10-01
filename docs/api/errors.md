# API Errors

> Error shapes and status codes the API actually returns.

## Status

**Implemented** (FastAPI defaults plus two custom cases).

| Status | When | Body |
| --- | --- | --- |
| 200/201/204 | success (204 for delete) | resource / none |
| 404 | `GET/PATCH/DELETE /X/{id}` for a missing row | `{"detail":"projects not found"}` (message uses the route tag: `channels`, `sources`, `transcripts`, `topics`, `collections`, `projects`, `scripts`, `scenes`, `assets`, `renders`) |
| 409 | unique violation (duplicate `(platform, external_id)`, topic slug, collection name, `(source_video_id, version)`…) **or** foreign key to a non-existent row | `{"detail":"conflict or invalid reference"}` |
| 422 | invalid body/query/path: wrong type, unknown enum, bad UUID, `limit` outside 1–200, unknown PATCH field, bad topic slug pattern, empty required string | FastAPI validation list: `{"detail":[{"loc":[...],"msg":"...","type":"..."}]}` |
| 503 | `GET /health/ready` when DB or pgvector missing | `{"status":"not_ready","database":bool,"pgvector":bool}` |
| 500 | unhandled errors: database unreachable on a CRUD call; a `PATCH` value longer than the column allows (the `*Update` schemas have no length limits, so the database rejects it with a `DataError`, which `crud.py` does not catch); any `StoryWeaverError` raised inside a route (not mapped to a status, [KI-8](../reference/status.md#known-issues-and-limitations)) | FastAPI default `{"detail":"Internal Server Error"}` |

409 is deliberately generic: the database error text is not leaked, and the same message covers duplicates and bad references. Callers cannot tell them apart from the response alone.

## Known quirks (code-level, documented as-is)

- **Explicit `null` in a `PATCH`.** `crud.py` applies `model_dump(exclude_unset=True)`, and the update schemas allow `None`. Sending `{"description": null}` **clears** a nullable column. Sending `{"title": null}` or `{"status": null}` on a NOT NULL column reaches the database, raises an integrity error, and is reported as the generic **409** `conflict or invalid reference` — which is misleading (it is neither a duplicate nor a bad reference). To leave a field unchanged, omit it. See [KI-4](../reference/status.md#known-issues-and-limitations).
- **No length limits on `PATCH`.** Create schemas bound string lengths (e.g. `title` 1–512); update schemas do not, so an over-long value returns **500** rather than 422.
- **Typed domain errors are not mapped.** `ProviderNotConfiguredError`, `UnsafePathError`, `InvalidSourceError` etc. have no exception handler ([KI-8](../reference/status.md#known-issues-and-limitations)). No current route raises them.

## Not implemented

Error codes/machine-readable `code` field, problem+json, per-field conflict reporting, request IDs. A DB outage currently yields 500 rather than 503 on CRUD routes.

## Error persistence for jobs

Distinct from HTTP errors: long-running work should record failures in `error`/`status` columns on the failing entity ([data-lifecycle](../data/data-lifecycle.md), [workflows/retry-and-recovery](../workflows/retry-and-recovery.md)); `LocalRunner` also logs `workflow.failed`.

Related: [API-conventions](API-conventions.md)

## Examples

```http
GET /api/v1/projects/3f2c0000-0000-0000-0000-000000000000  → 404
{"detail":"projects not found"}

POST /api/v1/sources  (same platform + external_id twice)   → 409
{"detail":"conflict or invalid reference"}

PATCH /api/v1/projects/{id}  {"status":"nope"}              → 422
{"detail":[{"type":"enum","loc":["body","status"],"msg":"Input should be 'draft', 'analyzing', ...","input":"nope","ctx":{"expected":"'draft', 'analyzing', ..."}}]}

PATCH /api/v1/projects/{id}  {"title":null}                 → 409   (NOT NULL column, see quirks)
{"detail":"conflict or invalid reference"}
```
