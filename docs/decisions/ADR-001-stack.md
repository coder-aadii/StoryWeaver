# ADR-001: Technology stack and module boundaries

Status: accepted · Date: 2026-10-01

## Decisions

1. **Python/FastAPI backend** (not Rails): the AI/media ecosystem (faster-whisper, yt-dlp, model SDKs) is Python.
2. **Modular monolith**: one deployable; `services/` stays empty until a module needs separate scaling/runtime
   (likely a GPU worker). Avoids distributed-system cost on a 16 GB laptop.
3. **PostgreSQL + pgvector** as source of truth and vector store; no separate vector DB.
4. **Synchronous SQLAlchemy 2 + psycopg 3**: simpler, ample for a single-user local tool; FastAPI runs sync
   endpoints in a threadpool. Revisit if request concurrency becomes a problem.
5. **Workflow abstraction first, Temporal later**: `WorkflowRunner` with an in-process implementation keeps first boot
   dependency-free. Temporal is a compose profile, not wired in.
6. **Remotion + FFmpeg** for deterministic video from a Timeline JSON; AI never performs media operations.
7. **Enums as VARCHAR**; `metadata` JSONB columns for extensible attributes (exposed as `meta` in Python because
   `metadata` is reserved on SQLAlchemy models).
8. **Postgres host port 5433** in compose to coexist with a local Postgres.
9. **Next.js dev port 3100**, as 3000 is frequently occupied.
10. **Embedding dimension fixed at 768** in the schema (matches common local embedding models); changing it is a migration.

## Consequences / known gaps

- No auth; localhost only.
- Provider adapters are only mock-tested; expect fixes on first real use.
- `CharacterVersion`, visual-style entities and tags are deferred until there is a consumer.
