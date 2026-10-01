# Integration Testing

> Tests that exercise real PostgreSQL, Alembic and pgvector.

## Status

Implemented.

## Fixture design (`apps/api/tests/conftest.py`)

- Session-scoped `engine`: skips unless `TEST_DATABASE_URL` is set and reachable; **first checks it is safe to wipe** (`tests/db_safety.py`: the database name must end in `_test` — override with `STORYWEAVER_ALLOW_DESTRUCTIVE_TESTS=1` — and it must not be the application's `DATABASE_URL`; this runs before any DDL, previously KI-19). It then resets the cached settings/engine/sessionmaker, runs `alembic downgrade base` + `upgrade head` — so every run validates the migrations from scratch. **It still destroys all data in that database**, so use a disposable one.
- Isolation: `conftest.py` overrides `DATABASE_URL` and provider keys in the environment for the whole session (so a DB-less test can never reach a real database or provider) and resets the cached settings, engine and sessionmaker around the DB fixtures; results are order-independent (previously KI-11, resolved in P0). `tests/test_migrations.py` checks up → down → up and `alembic check`.
- `db`: a Session; after each test, `TRUNCATE ... CASCADE` on all tables except `alembic_version`.
- `client`: `TestClient` with `get_db` overridden to the test session.
- `api` (P1): a `TestClient` whose requests each get their **own** session (like production), with background work run inline (`InlineRunner`) and `STORAGE_ROOT` pointed at a temp directory (`storage_root`), so uploads and raw transcript files never touch the repository's `data/`. Used by the Source Library API and service tests.

## Covered (`test_models.py`, `test_migrations.py`, and the DB-backed cases in `test_api.py`, `test_api_hardening.py`, `test_health.py`)

Migrations up → down → up and `alembic check` (`test_migrations.py`); API round trips, 404/409 bodies with `code`, valid PATCH and clearing nullable fields. Source Library schema (`test_models_p1.py`): upload sources (null `url`, `kind`), the partial unique index allowing one current transcript per source, the generated `search_vector` + GIN index, `workflow_runs` constraints (`test_runs.py`: one active run per `(kind, subject)`, lifecycle, reconciliation). Models: defaults and timestamps; one `SourceVideo` shared by two projects (join table); unique `(scene_id, version)` on `scene_versions`; embedding round trip and nearest neighbour via `cosine_distance`. Also `/health/ready` against the real DB.

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
