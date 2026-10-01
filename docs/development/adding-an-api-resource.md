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

- **PATCH semantics:** `PATCH` applies only fields that were sent (`exclude_unset`). Give every `*Update` schema `min_length`/`max_length` limits and list the columns that may be cleared in `nullable_fields` (the `_Patch` base rejects `null` for everything else with a 422). Previously KI-4, resolved in P0.
- Typed `StoryWeaverError`s raised in a route are mapped to HTTP statuses with a stable `code` by `install_exception_handlers`; expected client-visible failures can raise `ApiError(status, code, message)` (previously KI-8, resolved in P0). Add a mapping row in `api/errors.py` for any new error class.
- No total count/pagination metadata, no filtering/sorting parameters, no auth, no optimistic concurrency, no endpoints for join tables (`collection_videos`, `project_sources`) or for `script_versions`/`scene_versions`. See [API conventions](../api/API-conventions.md).

> Working as an AI coding agent? Read [AI agent guide](ai-agent-guide.md) first.
