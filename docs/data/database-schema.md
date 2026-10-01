# Database Schema Reference

> Column-level description of every table as created by the Alembic migrations `5d669179817c_initial_schema` and `e39be38b3620_p1_source_library`.

## Status

**Implemented.** 18 tables (17 domain tables + `workflow_runs`, added in P1). Source of truth: `apps/api/app/models/domain.py` and `apps/api/alembic/versions/`. `alembic check` reports no drift; the P1 migration is covered by an up → down → up test. The first migration also runs `CREATE EXTENSION IF NOT EXISTS vector`. A database created before P1 (including a hosted one) must be upgraded with `make db-migrate` before running the current API.

Common to all entity tables (except the two join tables): `id UUID PK` (Python-side `uuid4` default), `created_at`, `updated_at` (`timestamptz NOT NULL`, **server default `now()`**; `updated_at` is refreshed by SQLAlchemy `onupdate`, not by a DB trigger). Join tables have `created_at`/`updated_at` but a composite PK. All foreign-key columns are indexed. "Cascade" = `ON DELETE CASCADE`.

**Defaults live in Python, not in DDL.** Apart from `now()` on the two timestamps there are no server-side defaults. Values such as `status=draft`, `transcripts.version=1`, `origin=unknown`, `platform=youtube`, `role=primary`, `settings={}` and `metadata={}` are applied by SQLAlchemy when a row is created through the ORM, so a row inserted with raw SQL must supply every NOT NULL column.

## Enums

Stored as `VARCHAR(32)` (`native_enum=False`), values lowercase. The migration creates **no CHECK constraint**, so the database itself accepts any string up to 32 characters in a status/type column; validity is enforced by the Pydantic API models and the Python enums only. Adding a value therefore needs no `ALTER TYPE`.

| Enum | Values |
| --- | --- |
| `SourceStatus` | discovered, importing, imported, failed |
| `TranscriptStatus` | pending, processing, ready, failed |
| `ProjectStatus` | draft, analyzing, scripting, storyboarding, generating, rendering, qa, completed, failed |
| `SceneStatus` | draft, ready, generating, failed |
| `AssetStatus` | pending, generating, ready, failed |
| `RenderStatus` | queued, rendering, completed, failed |
| `RunStatus` | queued, running, succeeded, failed, interrupted |
| `AssetType` | image, audio, voice, music, sfx, video, thumbnail, subtitle, reference, render |

## Tables

Legend: **NN** = NOT NULL, **null** = nullable. Types are PostgreSQL types as emitted by the migration. Unique constraints use the naming convention `uq_<table>_<first column>`.

### channels
| Column | Type | Null | Notes |
| --- | --- | --- | --- |
| `platform` | varchar(32) | NN | Python default `youtube` |
| `external_id` | varchar(128) | NN | |
| `title` | varchar(512) | NN | |
| `url` | varchar(2048) | NN | validated at the API on create (YouTube video URL for `platform=youtube`, `http(s)` otherwise); no database constraint |
| `status` | varchar(32) | NN | `SourceStatus`, default `discovered`; indexed |
| `video_count` | integer | null | |
| `error` | text | null | |
| `metadata` | jsonb | NN | Python attr `meta`, default `{}` |

Unique `(platform, external_id)`. Indexes: `ix_channels_status`.

### source_videos
| Column | Type | Null | Notes |
| --- | --- | --- | --- |
| `channel_id` | uuid | null | FK → channels, **SET NULL**; indexed |
| `platform` | varchar(32) | NN | default `youtube` |
| `external_id` | varchar(128) | NN | |
| `url` | varchar(2048) | null | NULL for uploaded transcripts (nullable since P1) |
| `kind` | varchar(16) | NN | `youtube` or `transcript`; Python default `youtube` (the migration back-filled existing rows) |
| `fingerprint` | varchar(64) | null | sha256 of the normalized transcript's token text; indexed `ix_source_videos_fingerprint` |
| `thumbnail_url` | varchar(2048) | null | remote URL string; never fetched by the server |
| `title` | varchar(1024) | NN | |
| `description` | text | null | |
| `duration_seconds` | double precision | null | |
| `published_at` | timestamptz | null | not exposed by the API |
| `language` | varchar(16) | null | |
| `status` | varchar(32) | NN | `SourceStatus`, default `discovered`; indexed |
| `error` | text | null | |
| `metadata` | jsonb | NN | default `{}` |

Unique `(platform, external_id)`. Indexes: `ix_source_videos_channel_id`, `ix_source_videos_status`, `ix_source_videos_fingerprint`. Uploads use `platform='upload'`, `external_id` = the fingerprint. There is still no sync cursor ([KI-23](../reference/status.md#known-issues-and-limitations)).

### transcripts
| Column | Type | Null | Notes |
| --- | --- | --- | --- |
| `source_video_id` | uuid | NN | FK → source_videos, cascade; indexed |
| `version` | integer | NN | Python default 1 |
| `status` | varchar(32) | NN | `TranscriptStatus`, default `pending`; indexed |
| `is_current` | boolean | NN | Python default true; the migration back-filled existing rows to true |
| `origin` | varchar(32) | NN | Python default `unknown` (only on failed placeholder rows); written values `manual`, `auto` (platform captions) and `upload` |
| `language` | varchar(16) | null | |
| `text` | text | null | the **cleaned** text (the raw file is stored separately) |
| `segments` | jsonb | NN | default `[]`; `[{start,end,text,speaker}]` with `start`/`end` null for plain text; written by the ingestion service from validated `TranscriptSegment`s |
| `raw_storage_key` | varchar(1024) | null | `transcripts/<source_id>/v<n>/raw.<ext>` under `STORAGE_ROOT` |
| `raw_sha256` | varchar(64) | null | hash of the raw file as received |
| `normalizer_version` | varchar(16) | null | e.g. `1` |
| `error` | text | null | |

Unique `(source_video_id, version)`; **partial unique index `uq_transcripts_current`** on `(source_video_id) WHERE is_current` — at most one current transcript per source. Indexes: `ix_transcripts_source_video_id`, `ix_transcripts_status`.

### transcript_chunks
| Column | Type | Null | Notes |
| --- | --- | --- | --- |
| `transcript_id` | uuid | NN | FK → transcripts, cascade; indexed |
| `chunk_index` | integer | NN | |
| `text` | text | NN | |
| `start_seconds`, `end_seconds` | double precision | null | |
| `token_count` | integer | null | |
| `embedding` | vector(768) | null | |
| `embedding_model` | varchar(128) | null | |
| `search_vector` | tsvector | NN | **generated** (`to_tsvector('simple', text)`, stored); never written by code |

Unique `(transcript_id, chunk_index)`. Indexes: `ix_transcript_chunks_transcript_id`; `ix_transcript_chunks_embedding_hnsw` — HNSW, `vector_cosine_ops`, `m=16`, `ef_construction=64` (unused: no embeddings are written yet); `ix_transcript_chunks_search_vector` — **GIN** on `search_vector` (keyword search).

### topics
`name` varchar(255) NN **unique**; `slug` varchar(255) NN **unique**; `description` text null. (Unique constraints provide the only indexes.)

### collections
`name` varchar(255) NN **unique**; `description` text null.

### collection_videos
PK `(collection_id → collections cascade, source_video_id → source_videos cascade)`; index `ix_collection_videos_source_video_id`. No other columns.

### projects
`title` varchar(512) NN; `description` text null; `status` varchar(32) NN (`ProjectStatus`, default `draft`; indexed `ix_projects_status`); `settings` jsonb NN (default `{}`, no defined keys); `error` text null.

### project_sources
PK `(project_id → projects cascade, source_video_id → source_videos cascade)`; `role` varchar(32) NN (default `primary`); index `ix_project_sources_source_video_id`.

### scripts
`project_id` uuid NN (FK → projects, cascade; indexed); `title` varchar(512) NN.

### script_versions
`script_id` uuid NN (FK → scripts, cascade; indexed); `version` integer NN; `content` jsonb NN (default `{}`); `prompt_version` varchar(64) null; `provider` varchar(64) null; `model` varchar(128) null. Unique `(script_id, version)`. Nothing enforces immutability of a version row.

### scenes
`project_id` uuid NN (cascade; indexed); `script_id` uuid null (FK → scripts, **SET NULL**; indexed); `sequence` integer NN; `status` varchar(32) NN (`SceneStatus`, default `draft`; indexed); `error` text null. Non-unique index `ix_scenes_project_sequence (project_id, sequence)`.

### scene_versions
`scene_id` uuid NN (FK → scenes, cascade; indexed); `version` integer NN; `data` jsonb NN (default `{}`; intended to validate as `SceneSpec`, but no write path validates it). Unique `(scene_id, version)`.

### characters / locations
Same shape in both: `project_id` uuid NN (cascade; indexed); `name` varchar(255) NN; `description` text null; `attributes` jsonb NN (default `{}`; **keys are undefined** — see [story-data-model](story-data-model.md#characters-and-locations)). Unique `(project_id, name)`.

### assets
| Column | Type | Null | Notes |
| --- | --- | --- | --- |
| `project_id` | uuid | NN | FK → projects, cascade; indexed |
| `scene_id` | uuid | null | FK → scenes, **SET NULL**; indexed |
| `type` | varchar(32) | NN | `AssetType`; indexed |
| `status` | varchar(32) | NN | `AssetStatus`, default `pending`; indexed |
| `storage_key` | varchar(1024) | null | |
| `mime_type` | varchar(128) | null | |
| `size_bytes` | bigint | null | |
| `checksum` | varchar(128) | null | sha256 hex |
| `error` | text | null | |
| `metadata` | jsonb | NN | default `{}` |

### workflow_runs
Persisted background runs (D1; used by the Source Library ingestion workflows, generalised by later phases). `kind` varchar(64) NN (`source.add`, `source.fetch_transcript`); `subject_type` varchar(32) NN; `subject_id` uuid NN (no foreign key — generic); `status` varchar(32) NN (`RunStatus`, default `queued`; indexed); `attempt` integer NN; `idempotency_key` varchar(255) NN **unique** (`<kind>:<subject_id>:<attempt>`); `params`, `progress` jsonb NN (default `{}`); `error` jsonb null (`{code, message, retryable}`); `started_at`, `finished_at` timestamptz null. Indexes: `ix_workflow_runs_status`, `ix_workflow_runs_subject` on `(subject_type, subject_id)`, and **partial unique index `uq_workflow_runs_active`** on `(kind, subject_id) WHERE status IN ('queued','running')` — one active run per kind and subject.

### renders
`project_id` uuid NN (cascade; indexed); `status` varchar(32) NN (`RenderStatus`, default `queued`; indexed); `timeline` jsonb NN (default `{}`; snapshot rendered); `output_asset_id` uuid null (FK → assets, **SET NULL**; indexed); `started_at`, `finished_at` timestamptz null; `error` text null.

### Index summary
Beyond primary keys and unique constraints: status indexes on `channels`, `source_videos`, `transcripts`, `projects`, `scenes`, `assets`, `renders`, `workflow_runs`; `ix_source_videos_fingerprint`; `ix_workflow_runs_subject`; partial unique `uq_transcripts_current` and `uq_workflow_runs_active`; GIN `ix_transcript_chunks_search_vector`; `assets.type`; one index per foreign-key column (`source_videos.channel_id`, `transcripts.source_video_id`, `transcript_chunks.transcript_id`, `collection_videos.source_video_id`, `project_sources.source_video_id`, `scripts/scenes/characters/locations/assets/renders.project_id`, `scenes.script_id`, `script_versions.script_id`, `scene_versions.scene_id`, `assets.scene_id`, `renders.output_asset_id`); composite `ix_scenes_project_sequence`; HNSW `ix_transcript_chunks_embedding_hnsw`.

## Current limitations

- `scene_versions.data`, `script_versions.content`, `renders.timeline` are not validated at the DB level; validation is application-side and not yet wired into any write path.
- Status/type columns have no CHECK constraint (see Enums); defaults are Python-side only.
- `scenes.sequence` is not unique per project (reordering without constraint conflicts); uniqueness is a *Decision pending*.
- No checks on `error`/`status` consistency.
- The downgrade of the P1 migration restores `source_videos.url` NOT NULL by giving URL-less (upload) rows a placeholder `upload://<external_id>` and drops `is_current`, so downgrading a database that holds several transcript versions loses which one was current.
- Embedding dimension 768 is baked into the column type (`EMBEDDING_DIM` in `models/domain.py`); `Settings.embedding_dimensions` is an independent, unchecked value, so a different embedding size fails at insert time and needs a migration ([embeddings-and-vector-search](embeddings-and-vector-search.md), [KI-6](../reference/status.md#known-issues-and-limitations)).
- Source usage exists only at project level (`project_sources`). No storage exists for used ideas, story candidates, analysis results, similarity records or artifact dependencies ([KI-22](../reference/status.md#known-issues-and-limitations)); options are in [story-data-model](story-data-model.md) and [source-data-model](source-data-model.md).

See [migrations](../development/migrations.md) and [database-development](../development/database-development.md).
