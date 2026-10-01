# Adding an API Resource

> Exact steps to expose a new table under `/api/v1`.

## Status

Implemented (pattern). Ten resources use it today; `characters` and `locations` tables exist but have **no routes** yet.

## Steps

1. **Enum** (if needed) in `app/models/enums.py` (`enum.StrEnum`).
2. **Model** in `app/models/domain.py` using `IdMixin`, `TimestampMixin`, `_fk(...)` and `_enum(...)`; export it from `app/models/__init__.py`.
3. **Migration**: `make db-revision m="..."`, review, `make db-migrate` ([migrations](migrations.md)).
4. **Schemas** in `app/schemas/resources.py`: `XCreate`, `XUpdate(_Patch)` (`extra="forbid"`), `XRead(ReadModel)` (`from_attributes`).
5. **Route**: add a tuple `(Model, XCreate, XUpdate, XRead, "/xs", "xs")` to the list in `app/api/v1/router.py`. `crud_router` provides `GET` list (`limit` 1–200 default 50, `offset`, newest first), `GET/{id}`, `POST`, `PATCH`, `DELETE`.
6. **Tests** in `tests/test_api.py` (happy path, 404, 422, 409).
7. **Docs**: new page under `docs/api/resources/` and [status](../reference/status.md).

## Requirements of the generic factory

`crud_router` assumes the model has a single UUID primary key named `id` and a `created_at` column (used for ordering). **Composite-key join tables** (`collection_videos`, `project_sources`) cannot use it and need a dedicated router.

## When not to use the generic factory

Resources needing validation across fields, upload handling, workflow triggers, or non-CRUD verbs need a dedicated router in `app/api/v1/`. Integrity errors are mapped to `409` by the factory; unknown ids to `404`.

## Known gaps in the generic CRUD

- **PATCH semantics ([KI-4](../reference/status.md#known-issues-and-limitations)):** `PATCH` applies only fields that were sent (`exclude_unset`), but an explicit `null` clears a nullable column and, on a NOT NULL column, raises an integrity error that the factory reports as a misleading `409`. Update schemas have **no length limits** (create schemas do), so an over-long string reaches the database and returns `500`. Add `max_length`/`min_length` and non-null constraints to new `*Update` schemas.
- Typed `StoryWeaverError`s are not mapped to HTTP statuses ([KI-8](../reference/status.md#known-issues-and-limitations)).
- No total count/pagination metadata, no filtering/sorting parameters, no auth, no optimistic concurrency, no endpoints for join tables (`collection_videos`, `project_sources`) or for `script_versions`/`scene_versions`. See [API conventions](../api/API-conventions.md).

> Working as an AI coding agent? Read [AI agent guide](ai-agent-guide.md) first.
