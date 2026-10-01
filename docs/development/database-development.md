# Database Development

> Working with the PostgreSQL + pgvector schema.

## Status

Implemented.

## Facts

- Models: `apps/api/app/models/domain.py` (17 tables), enums in `models/enums.py`. Reference: [Database schema](../data/database-schema.md).
- Primary keys are UUIDv4 generated in Python; `created_at`/`updated_at` are timezone-aware with server defaults (`updated_at` uses `onupdate`).
- Enums are stored as `VARCHAR(32)` (`native_enum=False`) so adding a value needs no `ALTER TYPE`.
- JSONB columns use `Mapped[dict[str, Any]]`; the `metadata` column is exposed as `meta`.
- Constraint naming convention is set on `Base.metadata` (ix/uq/ck/fk/pk) so Alembic diffs are stable.
- `transcript_chunks.embedding` is `vector(768)` with an HNSW cosine index (`m=16`, `ef_construction=64`). The dimension is hard-coded as `EMBEDDING_DIM` in `domain.py` (`Settings.embedding_dimensions` is a separate setting that is **not** linked to or checked against the column — [KI-6](../reference/status.md#known-issues-and-limitations)); changing the dimension needs a migration.
- Sessions: `get_db()` yields a `Session` from a lazily built engine (`pool_pre_ping=True`). Importing the app never connects.
- Foreign-key `ondelete`: `CASCADE` for owned children; `SET NULL` for optional links (`source_videos.channel_id`, `scenes.script_id`, `assets.scene_id`, `renders.output_asset_id`).

## Using pgvector

```python
select(TranscriptChunk).order_by(TranscriptChunk.embedding.cosine_distance(vec)).limit(5)
```

Covered by `test_embedding_roundtrip_and_cosine_search`. No embedding-generation workflow exists yet ([embeddings](../ai/embeddings.md)).

## Local databases

[Setup](setup.md) covers Docker vs Docker-free. Use a **separate** `storyweaver_test` database for tests — the test fixture is destructive ([KI-19](../reference/status.md#known-issues-and-limitations); see [testing](testing.md)). First-run `DATABASE_URL` guidance for Docker vs Docker-free is in [setup](setup.md#3-database). Schema changes go through [migrations](migrations.md).
