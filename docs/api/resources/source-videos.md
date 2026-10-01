# Sources API

> The Source Library HTTP API: add a YouTube video or a transcript, list/search/read sources, retry, attach a transcript, track project usage. Exposed at `/sources` (the table is `source_videos`).

## Status

**Implemented (P1, 2026-10-01).** Replaces the former generic CRUD for sources: `POST /sources` and any way to set `status` or `url` were removed, so every source is created through the validating service ([KI-12](../../reference/status.md#known-issues-and-limitations), resolved). Verified by API tests (fake extractor, real PostgreSQL) and **one** recorded live run against YouTube ([verification record](../../reference/status.md#verification-record)). No authentication (localhost only). Response models: `apps/api/app/schemas/source_api.py`; OpenAPI at `/openapi.json`.

Base: `/api/v1` · tables: [database-schema](../../data/database-schema.md#source_videos) · domain: [source-library](../../domains/source-library.md) · workflow: [ingestion workflow](../../workflows/ingestion-workflow.md)

## Endpoints

| Endpoint | Purpose | Success | Main errors |
| --- | --- | --- | --- |
| `POST /sources/from-url` `{url}` | Add a YouTube **video**; metadata + captions are fetched in a background run (no media) | `202` `{source, run, already_exists:false}`; `200` with `already_exists:true, match:"identity"` if it exists | `422 invalid_source` (not a YouTube video URL), `422 unsupported_kind` (channel/playlist), `409 provider_not_configured` (yt-dlp missing) |
| `POST /sources/from-transcript` (multipart: `file` **or** `text`; `title` required; `language?`, `reference_url?`) | Add a transcript with no remote origin | `201` `{source, transcript, already_exists:false}`; `200` `already_exists:true, match:"fingerprint"` | `422 invalid_input` / `unsupported_file_type` / `transcript_parse_error`, `413 file_too_large` |
| `POST /sources/{id}/transcript` (multipart: `file` or `text`, `language?`) | Attach, or replace with a new version, the transcript of an existing source — the no-captions fallback | `200` `SourceDetail`; identical content is a no-op | `409 source_busy` (import running), same parse/size errors, `404` |
| `GET /sources` `?status=&kind=youtube\|transcript&used=&limit=&offset=` | List | `200` `Page[SourceListItem]` (`limit` 1–200, default 50) | `422` bad filter |
| `GET /sources/search` `?q=&exclude_used=&source_id=&limit=&offset=` | Keyword search | `200` `Page[SearchHit]` (`limit` 1–50, default 20) | `422` missing/empty/over-200-char `q` |
| `GET /sources/{id}` | Detail (+ current transcript summary, active run) | `200` `SourceDetail` | `404 not_found` |
| `PATCH /sources/{id}` `{title?, description?}` | Edit | `200` `SourceDetail` | `422` (null title, over-long, any other field incl. `status`, `url`) |
| `DELETE /sources/{id}` | Remove source, its transcripts/chunks/runs and raw files | `204` | `409 source_in_use` (linked to a project), `404` |
| `GET /sources/{id}/transcript` `?limit=&offset=` | Current transcript: summary, cleaned `text`, paged `segments` (`limit` 1–1000, default 200). A *failed* current transcript is returned with its error and empty text | `200` `TranscriptContent` | `404 no_transcript` (none at all) |
| `GET /sources/{id}/chunks` `?limit=&offset=` | Chunks of the current transcript (`limit` 1–200, default 50) | `200` `Page[ChunkRead]` | `404 no_transcript` |
| `POST /sources/{id}/retry` | Re-run the missing half (full import if metadata is missing, transcript only otherwise); returns the active run if one exists | `202` `{run}` | `409 nothing_to_retry`, `404` |
| `GET /sources/{id}/usage` | Projects using the source | `200` `list[SourceUsage]` | `404` |
| `PUT /projects/{pid}/sources/{sid}` `{role?}` | Link a source to a project (idempotent; updates `role`) | `200` `ProjectSourceLink` | `404`, `409 source_not_ready` (only `imported` sources), `422` empty role |
| `DELETE /projects/{pid}/sources/{sid}` | Unlink (idempotent) | `204` | `404` project |
| `GET /projects/{pid}/sources` | Sources of a project | `200` `list[ProjectSourceLink]` | `404` |
| `GET /runs/{id}` · `GET /runs?subject_id=&limit=&offset=` | Poll a background run | `200` `RunRead` / `Page[RunRead]` | `404 not_found` |

Notes
- `GET /sources/search` is registered **before** `/sources/{id}`; otherwise `search` would be parsed as a UUID.
- `/transcripts` is read-only (`GET` list/detail); there is no `POST`/`PATCH`/`DELETE` ([transcripts](transcripts.md)).
- Errors use `{detail, code}`; validation errors from FastAPI keep a list under `detail` ([errors](../errors.md)).

## Models

`SourceListItem` — `id, title, platform, kind (youtube|transcript), url (null for uploads), thumbnail_url, duration_seconds, language, status, error, channel_title, transcript_status, transcript_error, chunk_count, searchable, usage_count, created_at, updated_at`. `searchable` and `usage_count` are **derived**: searchable ⇔ the current transcript is `ready` and has at least one chunk. `SourceDetail` adds `description, published_at, fingerprint, transcript (TranscriptSummary), active_run`. `RunRead` — `id, kind (source.add|source.fetch_transcript), subject_type, subject_id, status (queued|running|succeeded|failed|interrupted), attempt, progress {step, segment_count, chunk_count}, error {code, message, retryable}, started_at, finished_at, created_at`.

## Examples (captured from the running API; ids shortened)

Add a video — `POST /api/v1/sources/from-url` `{"url":"https://www.youtube.com/watch?v=dQw4w9WgXcQ"}` → `202` (returned before the background run starts, so the transcript fields are still empty):

```json
{
  "source": {"id": "6d2a56f0…", "title": "dQw4w9WgXcQ", "platform": "youtube", "kind": "youtube",
             "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "thumbnail_url": null, "duration_seconds": null,
             "language": null, "status": "importing", "error": null, "channel_title": null,
             "transcript_status": null, "transcript_error": null, "chunk_count": 0, "searchable": false,
             "usage_count": 0, "created_at": "2026-10-01T19:34:19+05:30", "updated_at": "2026-10-01T19:34:19+05:30"},
  "run": {"id": "8db142ea…", "kind": "source.add", "subject_type": "source_video", "subject_id": "6d2a56f0…",
          "status": "queued", "attempt": 1, "progress": {}, "error": null, "started_at": null,
          "finished_at": null, "created_at": "2026-10-01T19:34:19+05:30"},
  "already_exists": false, "match": null, "transcript": null
}
```

Poll — `GET /api/v1/runs/8db142ea…` once finished: `{"status":"succeeded","attempt":1,"progress":{"step":"done","segment_count":4,"chunk_count":1},"error":null,…}`. Adding the same video again (any URL form) returns `200` with `"already_exists": true, "match": "identity"` and starts no run.

Upload — `curl -F title=Notes -F file=@notes.txt localhost:8000/api/v1/sources/from-transcript` → `201`: `source.platform "upload"`, `kind "transcript"`, `url null`, `status "imported"`, plus a `transcript` summary. The same words again (any title, format or the `text` field) → `200`, `"already_exists": true, "match": "fingerprint"`.

Search — `GET /api/v1/sources/search?q=volcanoes` → `200`:

```json
{"items": [{"source": {"id": "6d2a56f0…", "title": "Volcanoes explained", "searchable": true, "…": "…"},
            "chunk_id": "f7ac9b36…", "chunk_index": 0,
            "snippet": "Welcome to the show. Today we talk about <mark>volcanoes</mark> . They erupt without warning.",
            "start_seconds": 0.0, "end_seconds": 15.25, "rank": 0.0608}],
 "total": 1, "limit": 20, "offset": 0}
```

`snippet` is HTML-escaped except for the `<mark>` tags around matches (render it as text; honour only `<mark>`). The search config is `'simple'`: whole-word matching, no stemming (`volcano` does not match `volcanoes`).

Errors (all `{detail, code}`): `422 unsupported_kind` — "this is a channel URL; channel and playlist import arrives in a later release — add a single video URL"; `409 provider_not_configured` — "yt-dlp is not installed; run `uv sync --extra ingestion`" (the shared error mapper uses 409 for every "not configured"); `422 transcript_parse_error` — "line 6: malformed timestamp line"; `422 unsupported_file_type` — "upload a .txt, .srt or .vtt file"; `409 nothing_to_retry`; `409 source_in_use` — "this source is used by a project; unlink it first".

## Validation and security

Only `.txt`/`.srt`/`.vtt` uploads (≤ `MAX_TRANSCRIPT_BYTES`, default 5 MB, UTF-8 with optional BOM); the client filename is sanitised and **never used as a path** (stored as `raw.<ext>`); `reference_url` must be `http(s)` and is stored as text, never fetched; pasted `text` is sniffed for VTT/SRT; search queries never raise (parameterised `websearch_to_tsquery`); only the query *length* is logged. See [file security](../../security/file-security.md), [input validation](../../security/input-validation.md).

Related: [transcripts](transcripts.md) · [channels](channels.md) · [source-data-model](../../data/source-data-model.md)
