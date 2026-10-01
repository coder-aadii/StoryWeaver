# Testing (Developer Guide)

> How to run and write tests day to day. Strategy lives in [Testing strategy](../testing/testing-strategy.md).

## Status

Implemented.

## Run

```bash
make test            # pytest + vitest (web) + vitest (video)
make test-api        # cd apps/api && uv run pytest
make test-web        # Vitest for apps/web and packages/video
make e2e             # Playwright; needs the dev stack running
```

Current test counts and what each layer covers: [testing strategy](../testing/testing-strategy.md) (the only place counts are kept).

### Running a single test

```bash
cd apps/api
uv run pytest tests/test_api.py::test_project_crud_roundtrip     # one test
uv run pytest tests/test_units.py -k youtube                     # by keyword
pnpm --filter @storyweaver/web exec vitest run src/lib/api.test.ts
pnpm --filter @storyweaver/video exec vitest run src/camera.test.ts
```

DB-backed tests (`test_api.py`, `test_models.py`, and `test_ready_with_database` in `test_health.py`) need `TEST_DATABASE_URL`:

| Database | `TEST_DATABASE_URL` |
| --- | --- |
| Docker Compose (unverified) | `postgresql+psycopg://storyweaver:storyweaver@localhost:5433/storyweaver_test` (create the database first) |
| Docker-free helper (verified) | the second URL printed by `make db-up-nodocker`: `postgresql+psycopg://postgres@/storyweaver_test?host=<repo>/data/temporary/pgdata` |

> **Destructive ([KI-19](../reference/status.md#known-issues-and-limitations)).** On first use the fixture runs `alembic downgrade base` then `upgrade head`, and it truncates every table after each test. Nothing checks that the URL is a throwaway database. Never point it at `storyweaver` or any database with data you want. Without the variable DB tests are skipped (not failed), so a green run can mean they never ran.
>
> Isolation caveat ([KI-11](../reference/status.md#known-issues-and-limitations)): the fixture clears the settings cache but not the cached engine, so test order matters.

## Writing tests

- API/DB: use the `client` and `db` fixtures from `apps/api/tests/conftest.py`; use `plain_client` to prove behaviour without a database.
- Providers: subclass `LLMProvider` with a fake `_complete`, or monkeypatch `httpx.Client` with `httpx.MockTransport` (see `test_ollama_provider_http_shape`).
- Web: Vitest + Testing Library (jsdom), files `src/**/*.test.{ts,tsx}`.
- Video: pure functions (camera math) and schema parse of `sample/timeline.json`.

Details per layer: [unit](../testing/unit-testing.md), [integration](../testing/integration-testing.md), [API](../testing/api-testing.md), [frontend](../testing/frontend-testing.md), [E2E](../testing/e2e-testing.md), [media](../testing/media-testing.md).
