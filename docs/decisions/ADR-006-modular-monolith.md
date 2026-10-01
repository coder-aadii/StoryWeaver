# ADR-006: Modular monolith, not microservices

> One FastAPI application with clear domain packages; split out a service only when forced.

## Status

Accepted · 2026-10-01 · **Implemented** (structure). Several modules are placeholders.

## Context

Single developer, 16 GB laptop, many moving parts (AI, media, DB, UI). Distributed systems would add operational cost without benefit at this scale.

## Decision

- Domain code lives in `apps/api/app/{ingestion,intelligence,story,visual,voice,video,quality,workflows}` plus `core`, `db`, `models`, `schemas`, `api`.
- Modules communicate through Python interfaces and shared schemas, not HTTP.
- The top-level `services/` directory is intentionally empty (README only). Introduce a separate deployable there only for independent scaling or a different runtime — the likely first case is a GPU/media worker.
- Long-running work goes through the `WorkflowRunner` abstraction so it can later move to a worker/Temporal without changing callers ([ADR-001](ADR-001-stack.md)).
- `packages/video` (Remotion, TypeScript) is separate because it is a different runtime; it consumes the timeline JSON contract.

## Alternatives considered

Microservices per pipeline stage; a Rails backend (rejected in ADR-001).

## Consequences

- Simple local boot and debugging; one migration history; shared transactions.
- Module boundaries are conventions, not enforced; discipline and review ([coding-standards](../development/coding-standards.md)) keep them clean. Import-linting is **Decision pending**.
- Heavy dependencies (yt-dlp, faster-whisper) are optional extras so they do not burden the base install.

See [backend-architecture](../architecture/backend-architecture.md), [adding-a-domain](../development/adding-a-domain.md), [scalability](../architecture/scalability.md).

## Revisit when

A module (likely media/GPU work) needs independent scaling or a different runtime, or module boundaries start eroding without import-linting.
