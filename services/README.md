# services/

Intentionally empty. Domain logic lives in `apps/api/app/{ingestion,intelligence,story,visual,voice,video,quality}`
as modules of one FastAPI application (see `docs/decisions/ADR-001-stack.md`). Split a module out into a
separate deployable here only when it needs independent scaling or a different runtime (e.g. a GPU worker).
