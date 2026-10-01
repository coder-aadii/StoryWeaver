# Integration Testing

> Tests that exercise real PostgreSQL, Alembic and pgvector.

## Status

Implemented.

## Fixture design (`apps/api/tests/conftest.py`)

- Session-scoped `engine`: skips unless `TEST_DATABASE_URL` is set and reachable; sets `DATABASE_URL` to it, clears the settings cache, then runs `alembic downgrade base` + `upgrade head` — so every run validates the migrations from scratch. **It destroys data in that database, and nothing verifies the URL points at a throwaway database** ([KI-19](../reference/status.md#known-issues-and-limitations)).
- Isolation caveat ([KI-11](../reference/status.md#known-issues-and-limitations)): the fixture clears the *settings* cache but not the cached `get_engine()`/`get_sessionmaker()`. `test_ready_with_database` (which uses the app's own engine) passes only because nothing builds that engine earlier in the session, so test ordering or an earlier DB-touching import can break it.
- `db`: a Session; after each test, `TRUNCATE ... CASCADE` on all tables except `alembic_version`.
- `client`: `TestClient` with `get_db` overridden to the test session.

## Covered (`test_models.py`)

Defaults and timestamps; one `SourceVideo` shared by two projects (join table); unique `(scene_id, version)` on `scene_versions`; embedding round trip and nearest neighbour via `cosine_distance`. Also `/health/ready` against the real DB.

## Running

```bash
make db-up-nodocker          # prints DATABASE_URL and TEST_DATABASE_URL
export TEST_DATABASE_URL=...
cd apps/api && uv run pytest                                   # everything
uv run pytest tests/test_models.py                              # one file (DB)
uv run pytest tests/test_models.py::test_embedding_roundtrip_and_cosine_search   # one DB test
```

`TEST_DATABASE_URL` format:

- Docker-free helper (verified): `postgresql+psycopg://postgres@/storyweaver_test?host=<repo>/data/temporary/pgdata` — exactly the second line the helper prints.
- Docker Compose (unverified): `postgresql+psycopg://storyweaver:storyweaver@localhost:5433/storyweaver_test`; the database must be created first (the compose file creates only `storyweaver`).

Without the variable the DB tests are skipped silently — compare the skipped count with [testing strategy](testing-strategy.md#layers).

## Gaps

No test for HNSW index usage, concurrency, cascade/`SET NULL` behaviour, or enum value changes. Workflow integration tests: none (no workflows). See [database development](../development/database-development.md).
