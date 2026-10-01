# Development Workflow

> The day-to-day loop for changing StoryWeaver: change, check, document — and commit only when asked.

## Status

Implemented (as convention). There is **no CI**; the local gates in [Quality gates](../testing/quality-gates.md) are the only enforcement.

## Daily loop

1. `make db-up` (or `make db-up-nodocker`), export `DATABASE_URL`, `make db-migrate`.
2. `make dev` — API on :8000 with `--reload`, web on :3100.
3. Make a change. Work in the module that owns the concern ([repository structure](repository-structure.md)).
4. `make format` then `make lint` then `make test` (export `TEST_DATABASE_URL` or DB tests silently skip; it must point at a disposable database — [KI-19](../reference/status.md#known-issues-and-limitations)). Counts and layers: [testing strategy](../testing/testing-strategy.md).
5. If you changed a Pydantic contract used by Remotion, `make schemas` and update `packages/video/src/types.ts` ([adding a Remotion composition](adding-a-remotion-composition.md)).
6. If you changed models, create a migration ([migrations](migrations.md)).
7. Stop at a green working tree. **Do not commit or push unless explicitly requested by the user.** When a commit is requested, never include `.env`, `data/*` contents, media or model files (`.gitignore` covers these) — see [coding standards](coding-standards.md#commits).

## Rules of thumb

- **AI decides content; code decides timing, assets and rendering** ([ADR-004](../decisions/ADR-004-ai-vs-deterministic-responsibilities.md)).
- Do not import a concrete provider from business logic; go through `intelligence.registry` ([adding a provider](adding-a-provider.md)).
- Nothing may connect, download or load a model at import/startup time (lazy initialisation).
- Failures are persisted on the entity (`status` + `error`) rather than crashing the project.
- Do not build features without a consumer; keep docs honest about Planned vs Implemented ([status](../reference/status.md)).

## Documentation

Update the relevant doc and [status](../reference/status.md) in the same change that alters behaviour.

## Current limitations

No pre-commit hooks, no CI, no release process. Decision pending.

> Working as an AI coding agent? Read [AI agent guide](ai-agent-guide.md) first.
