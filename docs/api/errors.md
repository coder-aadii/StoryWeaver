# API Errors

> Error shapes, status codes and stable machine codes the API returns.

## Status

**Implemented.** Domain and database errors share one body shape, `{"detail": <message>, "code": <stable code>}` (added in P0, previously KI-8). FastAPI's own request-validation errors (422) keep FastAPI's default shape.

| Status | `code` | When | Body |
| --- | --- | --- | --- |
| 200/201/204 | — | success (204 for delete) | resource / none |
| 404 | `not_found` | `GET/PATCH/DELETE /X/{id}` for a missing row | `{"detail":"projects not found","code":"not_found"}` (message uses the route tag: `channels`, `sources`, `transcripts`, `topics`, `collections`, `projects`, `scripts`, `scenes`, `assets`, `renders`) |
| 409 | `duplicate` | unique violation (duplicate `(platform, external_id)`, topic slug, collection name, `(source_video_id, version)`…) | `{"detail":"a record with these unique values already exists","code":"duplicate"}` |
| 409 | `invalid_reference` | foreign key to a non-existent row | `{"detail":"a referenced record does not exist","code":"invalid_reference"}` |
| 409 | `missing_value` / `conflict` | NOT NULL violation / any other integrity error | `code` is `missing_value` or `conflict` |
| 409 | `provider_not_configured` | a route used a provider that is not configured (none does today) | domain-error handler |
| 422 | — (FastAPI shape) | invalid body/query/path: wrong type, unknown enum, bad UUID, `limit` outside 1–200, unknown PATCH field, **`null` for a required field**, over-long string, bad topic slug, invalid URL on create | `{"detail":[{"type":"…","loc":[...],"msg":"…","input":…}]}` |
| 422 | `invalid_value` | the database rejected a value as too long/malformed (`DataError`) after validation | `{"detail":"a value is too long or malformed","code":"invalid_value"}` |
| 422 | `invalid_source` | `InvalidSourceError` raised inside a route (none does today) | domain-error handler |
| 400 / 413 | `unsafe_path` / `file_too_large` | `UnsafePathError` / `FileTooLargeError` raised inside a route (no upload route exists yet) | domain-error handler |
| 502 / 504 | `provider_error`, `provider_bad_response` / `provider_timeout` | a provider call failed, returned an unusable reply, or timed out (no route calls a provider yet) | domain-error handler |
| 503 | — | `GET /health/ready` when the DB or pgvector is unavailable | `{"status":"not_ready","database":bool,"pgvector":bool,"error":"<ExceptionType>"}` (type only; details are in the log) |
| 500 | `internal_error` | any other `StoryWeaverError` raised inside a route (generic message, no details); other unhandled errors give FastAPI's default `{"detail":"Internal Server Error"}` | |

Messages never contain database error text, SQL, URLs, headers or provider response bodies. Duplicate and bad-reference conflicts are now distinguished by `code`, derived from the PostgreSQL error class.

## Behavior of `PATCH`

- Only fields that were sent are applied (`exclude_unset`); unknown fields are rejected (422).
- An explicit `null` **clears** a nullable column (`description` on projects, topics, collections and source videos; `video_count` on channels; `text` on transcripts). `null` on any NOT NULL field (for example `title`, `status`, `name`) is rejected with **422** (`'title' cannot be null`). To leave a field unchanged, omit it. (Previously a misleading 409 — KI-4, resolved in P0.)
- Update schemas carry length limits (for example `title` 1–512), so an over-long value is a 422 validation error rather than a database failure.

## Known limits

- FastAPI's validation 422 echoes the offending `input` back in its body; do not send secrets in request bodies you expect to log.
- A database outage on a CRUD call surfaces as an unhandled 500 rather than 503 (only `/health/ready` reports it as 503).
- Not implemented: problem+json, per-field conflict reporting, request IDs.

## Error persistence for jobs

Distinct from HTTP errors: long-running work should record failures in `error`/`status` columns on the failing entity ([data-lifecycle](../data/data-lifecycle.md), [workflows/retry-and-recovery](../workflows/retry-and-recovery.md)); `LocalRunner` also logs `workflow.failed`.

Related: [API-conventions](API-conventions.md)

## Examples

```http
GET /api/v1/projects/3f2c0000-0000-0000-0000-000000000000  → 404
{"detail":"projects not found","code":"not_found"}

POST /api/v1/sources  (same platform + external_id twice)   → 409
{"detail":"a record with these unique values already exists","code":"duplicate"}

POST /api/v1/scenes  {"project_id":"<unknown uuid>","sequence":1}  → 409
{"detail":"a referenced record does not exist","code":"invalid_reference"}

PATCH /api/v1/projects/{id}  {"title":null}                 → 422
{"detail":[{"type":"value_error","loc":["body"],"msg":"Value error, 'title' cannot be null","input":{"title":null},"ctx":{"error":{}}}]}

PATCH /api/v1/projects/{id}  {"title":"<600 characters>"}   → 422
{"detail":[{"type":"string_too_long","loc":["body","title"],"msg":"String should have at most 512 characters", …}]}

POST /api/v1/sources  {"url":"https://evil.example/x", …}   → 422
{"detail":[{"type":"value_error","loc":["body"],"msg":"Value error, not a YouTube URL", …}]}
```
