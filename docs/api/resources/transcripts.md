# Transcripts API

> CRUD for `transcripts` of a source video.

## Status

**Implemented** as plain CRUD for transcript rows. Transcript extraction/transcription workflows, cleaning and chunking persistence are **Planned — not implemented**; there is no API for `transcript_chunks`.

Base: `/api/v1/transcripts` · table: [database-schema](../../data/database-schema.md#transcripts)

## Create — `POST /transcripts` → 201
Required: `source_video_id` (unknown → 409). Optional: `origin` (default `upload`), `language`, `text`, `segments` (list of objects, stored as JSONB; **not validated** as `TranscriptSegment`). The server sets `version=1` and `status=pending`; a second transcript for the same video therefore returns **409** (version cannot be supplied; `unique(source_video_id, version)`). Transcript versioning is a **target**, not current API behavior ([KI-13](../../reference/status.md#known-issues-and-limitations)); multi-version support through the API: *Decision pending*. `origin` is free text: the API schema defaults it to `upload`, the database default is `unknown` (rows inserted outside the API get `unknown`). The model holds a single `text` plus `segments`; a raw-vs-cleaned split and any raw file location are *Decision pending* (no storage column exists).

## Read model
`id, created_at, updated_at, source_video_id, version, status, origin, language, text, error`. `segments` are stored but **not returned**, and because `TranscriptUpdate` allows only `status` and `text`, `segments` **cannot be modified after creation** through the API.

## Update — `PATCH /transcripts/{id}`
Allowed: `status` (`pending|processing|ready|failed`), `text`.

## Other
List/get/delete standard. Deleting removes chunks.

Related: [transcript-pipeline](../../domains/transcript-pipeline.md) · [source-data-model](../../data/source-data-model.md) · [embeddings-and-vector-search](../../data/embeddings-and-vector-search.md)

Example create body and response (`201`):
```json
{"source_video_id":"7d4e…","origin":"upload","language":"en","text":"Long ago the ice reached the sea.","segments":[{"start":0,"end":3.1,"text":"Long ago the ice reached the sea."}]}
```
```json
{"id":"c2a9…","created_at":"…","updated_at":"…","source_video_id":"7d4e…","version":1,"status":"pending","origin":"upload","language":"en","text":"Long ago the ice reached the sea.","error":null}
```
