# ADR-005: PostgreSQL + pgvector as the single data store

> One database for relational metadata and vector search; no separate vector DB.

## Status

Accepted · 2026-10-01 · **Implemented** (schema, migration, HNSW index, nearest-neighbour test). Embedding generation is Planned — not implemented.

## Context

The system needs relational integrity (sources, projects, scenes, versions, assets) and semantic search over transcript chunks. Volume is modest (hundreds to low thousands of videos on one machine).

## Decision

- PostgreSQL is the source of truth for application metadata; binary media stays on disk ([ADR-008](ADR-008-storage-strategy.md)).
- `pgvector` provides `transcript_chunks.embedding vector(768)` with an HNSW index (`vector_cosine_ops`, m=16, ef_construction=64).
- Alembic owns schema; the first migration runs `CREATE EXTENSION IF NOT EXISTS vector`.
- Flexible attributes use JSONB (`metadata`, `settings`, `attributes`, scene/script `content`/`data`); statuses are VARCHAR-backed enums so adding a value needs no `ALTER TYPE`.
- Dev image: `pgvector/pgvector:pg16` (Compose, host port 5433). A Docker-free path uses a user-space Postgres 16 with pgvector.

## Alternatives considered

- Dedicated vector DB (Qdrant, Chroma…): extra service on a 16 GB machine, split consistency; rejected for now.
- SQLite + extension: weaker concurrency/JSONB/migration story; rejected.

## Consequences

- **Embedding dimension is fixed at 768 in the schema** (the `EMBEDDING_DIM` constant in `models/domain.py`). `Settings.embedding_dimensions` is a separate value that is **not linked or checked** against the column ([KI-6](../reference/status.md#known-issues-and-limitations)); changing the setting does nothing to the schema, and a model with a different size fails at insert time. A different-sized model requires a migration and re-embedding. Policy for model changes: **Decision pending** ([embeddings](../ai/embeddings.md)).
- An embedding model name is stored per chunk (`embedding_model`) so stale vectors are detectable.
- A local Postgres without pgvector (e.g. system Postgres 12) cannot run the migration.
- Synchronous SQLAlchemy 2 + psycopg 3 is used (ADR-001); revisit if concurrency demands.

Details: [database-schema](../data/database-schema.md), [embeddings-and-vector-search](../data/embeddings-and-vector-search.md), [database-development](../development/database-development.md).

## Revisit when

Vector volume or query latency outgrows pgvector on one machine, or the embedding model changes dimension.
