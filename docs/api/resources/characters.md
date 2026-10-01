# Characters API

> Status of API access to the character bible.

## Status

**Planned for the API — not implemented.** The `characters` table (and `locations`) is **Implemented**, but **no `/characters` route exists** in `api/v1/router.py`; requests to it return 404. Rows can currently only be created directly in the database. `GET /api/v1/characters` returns FastAPI's default `{"detail":"Not Found"}`. `locations` is in the same position.

## What exists

Table `characters`: `project_id`, `name` (unique per project), `description`, `attributes` JSONB ([database-schema](../../data/database-schema.md#characters--locations)). `CharacterVersion` is **Deferred until required by the production workflow**.

## Target (Decision pending)

A conventional resource `/characters` (CRUD, filtered by `project_id`), with reference-image linking via assets and version history if `CharacterVersion` is introduced. Adding it is a router-table entry plus Pydantic schemas ([adding-an-api-resource](../../development/adding-an-api-resource.md)). `/locations` is in the same position.

Related: [domains/character-system](../../domains/character-system.md) · [story-data-model](../../data/story-data-model.md#characters-and-locations)
