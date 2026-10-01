# Source Data Model

> Tables and contracts for the source library: channels, videos, transcripts, chunks, topics, collections.

## Status

**Partially implemented.** Tables, API CRUD for channels/videos/transcripts/topics/collections, `NormalizedSource`, YouTube URL classification and transcript chunking exist. No workflow populates them; no topic/collection membership endpoints. Product design: [domains/source-library](../domains/source-library.md).

## Entities

| Entity | Identity | Key fields | Notes |
| --- | --- | --- | --- |
| `Channel` | unique `(platform, external_id)` | `title`, `url`, `status`, `video_count`, `error`, `metadata` | `video_count` is set by a future scan. `external_id` is caller-supplied; if later derived from the URL fragment (`@handle`, `channel/UC…`) a renamed channel could create a duplicate — the canonical id must come from extractor output ([KI-24](../reference/status.md#known-issues-and-limitations)) |
| `SourceVideo` | unique `(platform, external_id)` | `url`, `title`, `description`, `duration_seconds`, `published_at`, `language`, `status`, `error`, `metadata`, `channel_id?` | one row however many projects use it |
| `Transcript` | unique `(source_video_id, version)` | `status`, `origin`, `language`, `text`, `segments`, `version`, `error` | the schema allows several versions, but the API cannot set `version` (default 1) so a second transcript returns 409 — versioning is a **target** ([KI-13](../reference/status.md#known-issues-and-limitations)) |
| `TranscriptChunk` | unique `(transcript_id, chunk_index)` | `text`, `start_seconds`, `end_seconds`, `token_count`, `embedding`, `embedding_model` | the unit of retrieval |

## NormalizedSource (Pydantic, implemented)

Platform-neutral output of any `SourceExtractor` (`apps/api/app/schemas/source.py`): `platform`, `kind` (`video|channel|playlist|transcript|file`), `external_id`, `url`, `title`, `description?`, `duration_seconds?`, `published_at?`, `language?`, `channel_external_id?`, `channel_title?`, `segments: TranscriptSegment[]`, `extra`. `TranscriptSegment`: `start`, `end`, `text`, `speaker?`. Mapping `NormalizedSource` → rows is *Planned — not implemented* (no persistence code calls it yet; `channel_external_id` has no mapping to the `source_videos.channel_id` UUID FK). Today `YouTubeExtractor.extract()` returns metadata only and never populates `segments` ([KI-15](../reference/status.md#known-issues-and-limitations)).

## Transcript representation

- `text` — a single string (no raw-vs-cleaned distinction is stored).
- `segments` — JSONB list of timestamped segments. Raw vs cleaned transcripts as separate artefacts: *Decision pending* (today: one `text` + `segments`). A raw file under `data/transcripts/` is one option, but **the schema has no column to record its storage key**, so that option also needs a migration (or a convention in a `metadata` field, which transcripts do not have). See [storage-layout](storage-layout.md).
- `origin` — free string (`manual|auto|whisper|upload` intended); not enforced. Default is `unknown` in the database/model and `upload` in the API create schema.
- Chunking: `chunk_segments(segments, max_chars=1200)` returns `(text, start, end)` tuples; writing them to `transcript_chunks` is not wired.

## Organisation

- `topics`: `name`, `slug`, `description` — flat, no hierarchy, no link to videos/chunks yet.
- `collections` + `collection_videos`: many-to-many with videos. **No API endpoint adds/removes members** (table only).
- Duplicate detection is by the unique `(platform, external_id)` constraint — a second insert returns 409 via the API. Content-level duplicate detection: *Planned — not implemented*.

## Status lifecycle

`SourceStatus`: `discovered → importing → imported | failed`. `imported` means **metadata stored** (see [workflows/ingestion-workflow](../workflows/ingestion-workflow.md)); a source is *searchable* only when it also has a `ready` transcript with chunks and embeddings — that is derived, not a status value. `TranscriptStatus`: `pending → processing → ready | failed`. Transitions are not enforced by code; the API allows PATCHing any valid status.

## Related

[embeddings-and-vector-search](embeddings-and-vector-search.md) · [domains/transcript-pipeline](../domains/transcript-pipeline.md) · [domains/channel-ingestion](../domains/channel-ingestion.md) · [api/resources/source-videos](../api/resources/source-videos.md)

## Target-model gaps (verified absent from the schema)

| Concern | Today | Target / status |
| --- | --- | --- |
| Source flow | code only: `SourceExtractor → NormalizedSource`; persistence of it does not exist | Canonical chain and provider-independence rule: [domains/source-library](../domains/source-library.md). YouTube specifics stay in `ingestion/youtube.py`; the data model has only a generic `platform` column plus `NormalizedSource` |
| Identity / dedup | unique `(platform, external_id)` | No content fingerprint (hash of normalized transcript, near-duplicate detection across platforms/re-uploads). Planned — not implemented; *Decision pending* on column vs. table |
| Uploaded transcripts without a remote origin | not representable: `source_videos.url` and `external_id` are NOT NULL and `TranscriptCreate` needs a `source_video_id` | A convention (e.g. `platform=upload`, synthetic `external_id` such as a content hash, `url` as a `local:` URI) or relaxing the columns — *Decision pending* ([KI-14](../reference/status.md#known-issues-and-limitations)) |
| Source usage / idea reuse | `project_sources` links video↔project, no endpoint | Not modelled — see [storage direction below](#source-usage-and-idea-reuse--storage-direction-decision-pending) ([KI-22](../reference/status.md#known-issues-and-limitations)) |
| Thumbnail | no column | `Asset(type=thumbnail)` is **not usable as-is**: `assets.project_id` is NOT NULL, so a library-level thumbnail cannot exist without a project. Options: a nullable `thumbnail_url` on `source_videos`, a `metadata`-held URL, or relaxing `assets.project_id` — *Decision pending* ([KI-23](../reference/status.md#known-issues-and-limitations)) |
| Incremental channel sync | no `last_synced_at`, cursor or per-video "seen" state; `channels.metadata` JSONB is the only place | Planned — not implemented ([workflows/channel-sync-workflow](../workflows/channel-sync-workflow.md)) |
| Transcript provenance | `version` + `origin` exist | origin is an unconstrained string; no link to the extractor/model/settings used |
| Source analysis artifacts and their caching | none | Storage options: [story-data-model](story-data-model.md#story-candidate-and-source-analysis-storage-options-decision-pending) |

## Source usage and idea reuse — storage direction (Decision pending)

Goal ([domains/source-library](../domains/source-library.md)): remember which sources, facts and ideas have been used by which project, so later work can avoid repeating them or find unused material ("unused ideas in my History collection"). Nothing is stored today.

| Option | Shape | Notes |
| --- | --- | --- |
| 1. Source-level usage only | add usage metadata to `project_sources` (e.g. `role`, `used_at`) | Cheap; says *that* a source was used, not *what* from it |
| 2. Usage records | new `source_usages` table: `source_video_id`, optional `transcript_chunk_id` / time range, `project_id`, optional artifact id (the story candidate or script it fed), `kind` (fact / idea / story), timestamps | Answers "which parts of this source were used where"; needs an artifact model to reference ([story-data-model options](story-data-model.md#story-candidate-and-source-analysis-storage-options-decision-pending)) |
| 3. Idea embeddings | store an embedding per accepted idea/story summary and compare new candidates against them | Enables "avoid previously used ideas" semantically rather than by exact match; design in [embeddings-and-vector-search](embeddings-and-vector-search.md#originality-and-similarity-data-direction) |

Options 2 and 3 are complementary. None is chosen; *Deferred until required by the production workflow*.
