# Data Model Overview

> Entry point for StoryWeaver's persistent data: what is stored where, and which parts are real today.

## Status

**Partially implemented.** All 17 tables, the Alembic migration and the pgvector index are implemented and tested. Almost no application logic writes to them yet (only the generic CRUD API does), and several JSONB payloads have a schema in code but no producer.

## Principles (implemented)

1. **PostgreSQL is the source of truth for metadata** ([ADR-005](../decisions/ADR-005-postgres-pgvector.md)). Binary media is never stored in PostgreSQL; rows hold a `storage_key` into `data/` ([storage-layout](storage-layout.md)).
2. **UUID primary keys** (`uuid.uuid4`, generated in Python) on every entity table; join tables use composite keys.
3. **Timestamps**: `created_at` / `updated_at` (timezone-aware, server default `now()`, `updated_at` refreshed on ORM update).
4. **Statuses are explicit enums** stored as VARCHAR(32), not native PG enums — adding a value needs no `ALTER TYPE`, and the database has no CHECK constraint (validity is enforced by Python/Pydantic only). See [database-schema](database-schema.md#enums).
5. **Versioning by child table**: `script_versions` and `scene_versions` are unique on `(parent_id, version)`.
6. **Per-entity error capture**: `error TEXT` columns on channels, source_videos, transcripts, projects, scenes, assets, renders so a failure is recorded on the entity that failed, not on the whole project.
7. **Extensibility via JSONB**: `metadata`, `settings`, `attributes`, `segments`, `content`, `data`, `timeline`. The Python attribute for the `metadata` column is `meta` (SQLAlchemy reserves `metadata`).

## Groups

| Group | Tables | Doc |
| --- | --- | --- |
| Source library | `channels`, `source_videos`, `transcripts`, `transcript_chunks` | [source-data-model](source-data-model.md) |
| Organisation | `topics`, `collections`, `collection_videos` | [source-data-model](source-data-model.md#organisation) |
| Projects | `projects`, `project_sources` | [project-data-model](project-data-model.md) |
| Story / script | `scripts`, `script_versions` | [story-data-model](story-data-model.md) |
| Scenes | `scenes`, `scene_versions` | [scene-data-model](scene-data-model.md) |
| Visual bible (partial) | `characters`, `locations` | [story-data-model](story-data-model.md#characters-and-locations) |
| Media | `assets`, `renders` | [asset-data-model](asset-data-model.md) |

Relationship diagram: [entity-relationships](entity-relationships.md). Column-level reference: [database-schema](database-schema.md).

## Pydantic contracts that are not tables

`apps/api/app/schemas/` holds validated shapes stored inside JSONB or passed between modules: `SceneSpec`, `Timeline`/`TimelineScene`, `NormalizedSource`, `TranscriptSegment`. Index: [reference/schemas](../reference/schemas.md).

## Not modelled (deliberately)

`CharacterVersion`, visual-style / era / object entities (and a Visual Bible entity), tags, job/workflow-run tables, token-usage and latency records, users/auth, story candidates and source-analysis artifacts, source-usage / used-idea records, similarity records, artifact dependency edges. Each is *Deferred until required by the production workflow* or *Decision pending*; storage options are in [story-data-model](story-data-model.md), [source-data-model](source-data-model.md), [embeddings-and-vector-search](embeddings-and-vector-search.md) and [asset-data-model](asset-data-model.md) ([KI-22](../reference/status.md#known-issues-and-limitations)). Observability is currently structured logs only ([operations/logging](../operations/logging.md)).

## Related

[data-lifecycle](data-lifecycle.md) · [embeddings-and-vector-search](embeddings-and-vector-search.md) · [architecture/domain-architecture](../architecture/domain-architecture.md)
