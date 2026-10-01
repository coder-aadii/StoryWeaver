# ADR-001: Technology stack and module boundaries

> Foundational stack and module-boundary choices for StoryWeaver. Several items are refined by later ADRs, which now own their topic.

## Status

*Amended 2026-10-01: rewritten in place with Context/Alternatives/Revisit sections and pointers to later ADRs (the only in-place rewrite; later ADRs are append-only).*

Accepted · 2026-10-01 · **Implemented** (foundation phase). Superseded in part by later ADRs, which are authoritative where they differ: item 2 → [ADR-006](ADR-006-modular-monolith.md); items 3, 7 and 10 → [ADR-005](ADR-005-postgres-pgvector.md); item 6 → [ADR-007](ADR-007-media-rendering-strategy.md) and [ADR-004](ADR-004-ai-vs-deterministic-responsibilities.md). Related: [ADR index](README.md).

## Context

A single developer is building an AI- and media-heavy product on a 16 GB, CPU-only laptop. The backend must host Python AI/media libraries (faster-whisper, yt-dlp, model SDKs); the UI must preview video; local setup must stay simple and optional services must not block first boot.

## Decisions

1. **Python/FastAPI backend** (not Rails): the AI/media ecosystem is Python. Pydantic for contracts, SQLAlchemy 2 + Alembic for persistence, `uv` for environments.
2. **Modular monolith** — one deployable; `services/` stays empty until a module needs separate scaling/runtime. *See [ADR-006](ADR-006-modular-monolith.md).*
3. **PostgreSQL + pgvector** as source of truth and vector store; no separate vector DB. *See [ADR-005](ADR-005-postgres-pgvector.md).*
4. **Synchronous SQLAlchemy 2 + psycopg 3**: simpler, ample for a single-user local tool; FastAPI runs sync endpoints in a threadpool. Revisit if request concurrency becomes a problem.
5. **Workflow abstraction first, Temporal later**: `WorkflowRunner` with an in-process implementation keeps first boot dependency-free. Temporal is a compose profile, not wired in ([workflow-architecture](../architecture/workflow-architecture.md)).
6. **Remotion for deterministic video from Timeline JSON; AI never performs media operations.** *See [ADR-007](ADR-007-media-rendering-strategy.md) (rendering) and [ADR-004](ADR-004-ai-vs-deterministic-responsibilities.md) (responsibility boundary).* Next.js/React/TypeScript/Tailwind/shadcn/Zustand/TanStack Query for the UI.
7. **Enums as VARCHAR**; `metadata` JSONB columns for extensible attributes (exposed as `meta` in Python because `metadata` is reserved on SQLAlchemy models).
8. **Postgres host port 5433** in compose to coexist with a local Postgres.
9. **Next.js dev port 3100**, as 3000 is frequently occupied.
10. **Embedding dimension fixed at 768** in the schema; changing it is a migration. *Details and the unlinked setting: [ADR-005](ADR-005-postgres-pgvector.md).*

## Alternatives considered

- **Rails backend:** strong conventions, weak AI/media ecosystem; rejected.
- **Async SQLAlchemy + asyncpg:** more moving parts for a single-user tool; deferred.
- **Microservices per stage:** rejected ([ADR-006](ADR-006-modular-monolith.md)).
- **Mandatory Temporal/Docker for first boot:** rejected; local setup must stay simple.

## Consequences / known gaps

- No auth; localhost only ([authentication](../api/authentication.md)).
- Only the Ollama chat adapter has a (mocked-HTTP) test; the embedding adapters and the other LLM adapters are untested and none has run against a real service ([ADR-003](ADR-003-provider-abstraction.md)); expect fixes on first real use.
- `CharacterVersion`, visual-style entities and tags are deferred until there is a consumer.
- Code-level defects found after this decision are tracked in [status — known issues](../reference/status.md#known-issues-and-limitations).

## Revisit when

Request concurrency outgrows sync endpoints; a module needs separate scaling (see ADR-006); the web app needs to be built fully offline (fonts are fetched at build time — [KI-25](../reference/status.md#known-issues-and-limitations)).
