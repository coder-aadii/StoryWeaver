# Source Videos API

> CRUD for `source_videos`, exposed at `/sources` (note the route name differs from the table name).

## Status

**Implemented** as plain CRUD. Fetching metadata from YouTube is not wired to this route; `YouTubeExtractor` exists in code but nothing calls it from the API (**Planned — not implemented**).

Base: `/api/v1/sources` · table: [database-schema](../../data/database-schema.md#source_videos)

## Create — `POST /sources` → 201
Required: `external_id` (≤128), `url` (≤2048), `title` (≤1024). Optional: `platform` (default `youtube`, ≤32), `channel_id` (UUID; unknown id → 409), `description` (≤20,000), `duration_seconds` (≥0), `language` (≤16). Duplicate `(platform, external_id)` → 409 `duplicate` (the project's current duplicate detection; content-level dedup is not implemented). **`url` is validated on create**: for `platform=youtube` it must be a YouTube **video** URL (`classify_youtube_url`; a channel or playlist URL is rejected), for other platforms an `http(s)` URL; violations are 422. `PATCH` cannot change `url`, and a future fetch of a stored URL must still re-validate it (previously KI-12). `url` and `external_id` are required, so a source with no remote origin (e.g. an uploaded transcript) is not representable without a convention ([KI-14](../../reference/status.md#known-issues-and-limitations)).

## Read model
`id, created_at, updated_at, channel_id, platform, external_id, url, title, description, duration_seconds, language, status, error`. Not exposed: `published_at`, `metadata`.

## Update — `PATCH /sources/{id}`
Allowed: `title`, `description`, `status`.

## Other
List/get/delete as per [API-conventions](../API-conventions.md). Delete cascades to transcripts and chunks and removes project/collection links ([data-lifecycle](../../data/data-lifecycle.md)).

Example response (`201`):
```json
{"id":"7d4e…","created_at":"2026-10-01T12:50:03.100000+05:30","updated_at":"2026-10-01T12:50:03.100000+05:30",
 "channel_id":null,"platform":"youtube","external_id":"dQw4w9WgXcQ","url":"https://youtu.be/dQw4w9WgXcQ",
 "title":"Example","description":null,"duration_seconds":null,"language":null,"status":"discovered","error":null}
```
`status` here is the import state of the source *record*; `imported` means metadata is stored — whether the source is searchable depends on its transcript and chunks ([source-library](../../domains/source-library.md)). There is no thumbnail field ([KI-23](../../reference/status.md#known-issues-and-limitations)).

```bash
curl -s -X POST localhost:8000/api/v1/sources -H 'content-type: application/json' \
  -d '{"external_id":"dQw4w9WgXcQ","url":"https://youtu.be/dQw4w9WgXcQ","title":"Example"}'
```

Related: [source-data-model](../../data/source-data-model.md) · [domains/source-library](../../domains/source-library.md)
