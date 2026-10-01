# Channels API

> CRUD for `channels` — imported/known YouTube (or other platform) channels.

## Status

**Implemented** as plain CRUD. Channel scanning, counting and import are **Planned — not implemented** ([domains/channel-ingestion](../../domains/channel-ingestion.md)); the API only stores records you send.

Base: `/api/v1/channels` · table: [database-schema](../../data/database-schema.md#channels) · conventions: [API-conventions](../API-conventions.md)

## Create — `POST /channels` → 201
| Field | Required | Notes |
| --- | --- | --- |
| `external_id` | yes | 1–128 chars |
| `title` | yes | 1–512 |
| `url` | yes | 1–2048; **not validated at all** — any string is accepted ([KI-12](../../reference/status.md#known-issues-and-limitations)). `classify_youtube_url` runs only inside the extractor, so API-created rows are not URL-checked and any future fetch must re-validate |
| `platform` | no | default `youtube` |

Duplicate `(platform, external_id)` → 409.

## Read model
`id, created_at, updated_at, platform, external_id, title, url, status, video_count, error`. (`metadata` is not exposed.)

## Update — `PATCH /channels/{id}`
Allowed: `title`, `status` (`discovered|importing|imported|failed`), `video_count`. Others → 422.

## Other
`GET /channels` (paged, [pagination](../pagination.md)), `GET /channels/{id}`, `DELETE` → 204 (videos keep existing, `channel_id` set NULL).

Note on identity: `external_id` is caller-supplied. If it is later derived from the URL fragment (`@handle`, `channel/UC…`), a renamed channel could produce a duplicate row; the canonical channel id should come from extractor output ([KI-24](../../reference/status.md#known-issues-and-limitations)). `PATCH` quirks (explicit `null`, no length limits): [errors](../errors.md#known-quirks-code-level-documented-as-is).

Example response (`201`):
```json
{"id":"0b1c…","created_at":"2026-10-01T12:48:42.273601+05:30","updated_at":"2026-10-01T12:48:42.273601+05:30",
 "platform":"youtube","external_id":"@SomeChannel","title":"Some Channel",
 "url":"https://www.youtube.com/@SomeChannel","status":"discovered","video_count":null,"error":null}
```

```bash
curl -s -X POST localhost:8000/api/v1/channels -H 'content-type: application/json' \
  -d '{"external_id":"@SomeChannel","title":"Some Channel","url":"https://www.youtube.com/@SomeChannel"}'
```

Related: [source-data-model](../../data/source-data-model.md) · [workflows/channel-sync-workflow](../../workflows/channel-sync-workflow.md)
