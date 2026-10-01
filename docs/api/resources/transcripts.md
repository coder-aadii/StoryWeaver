# Transcripts API

> Read-only access to transcript rows. Transcripts are created by the ingestion service, never by the API client.

## Status

**Implemented, read-only (P1, 2026-10-01).** `GET /transcripts` and `GET /transcripts/{id}` remain from the generic CRUD; `POST`, `PATCH` and `DELETE` were **removed** ([KI-13](../../reference/status.md#known-issues-and-limitations), resolved): versions are created by the service, so a client can no longer insert unvalidated segments or a conflicting `version`. Transcript *content* is read through the source routes below.

Base: `/api/v1/transcripts` · table: [database-schema](../../data/database-schema.md#transcripts)

## Endpoints

| Endpoint | Purpose |
| --- | --- |
| `GET /transcripts?limit=&offset=` | List rows (all versions of all sources) |
| `GET /transcripts/{id}` | One row |
| `POST` / `PATCH` / `DELETE /transcripts…` | **`405`** — not available |
| `GET /sources/{id}/transcript` | The source's **current** transcript: summary, cleaned `text`, paged `segments` ([sources API](source-videos.md)) |
| `GET /sources/{id}/chunks` | Its chunks (with timestamps) |
| `POST /sources/{id}/transcript` | Attach or replace (a new version) via upload/paste |

## Read model (`GET /transcripts/{id}`)

`id, created_at, updated_at, source_video_id, version, status (pending|processing|ready|failed), origin, language, text, error`. `segments`, the raw-file key and `normalizer_version` are not in this model; use `GET /sources/{id}/transcript` (`TranscriptSummary` adds `segment_count, char_count, timed, normalizer_version`). `origin` is `manual` / `auto` (platform captions) or `upload`; `unknown` appears only on failed placeholder rows (e.g. `no_captions`).

## Behaviour

- Exactly one version per source is current (`is_current`); older versions stay as history with their chunks but are not searchable.
- `timed` is `false` for plain `.txt` transcripts: `segments[].start/end` are `null`, and chunk times are `null`.
- A failed current transcript is visible (`status: failed`, `error: "no_captions: …"`) so the UI can offer an upload; it never replaces a ready one.

Related: [transcript-pipeline](../../domains/transcript-pipeline.md) · [source-data-model](../../data/source-data-model.md) · [embeddings-and-vector-search](../../data/embeddings-and-vector-search.md)
