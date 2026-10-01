# Adding a Domain Module

> How to introduce a new capability area (e.g. `story`, `quality`) inside the monolith.

## Status

Implemented (pattern). `story/` and `quality/` currently contain only a docstring.

## Steps

1. Create or fill `apps/api/app/<domain>/`. Keep a public surface of plain functions/classes and interfaces (ABC/Protocol) for anything with multiple implementations.
2. Contracts: structured Pydantic models under `app/schemas/` for anything produced by an LLM, so [structured output](../ai/structured-output.md) validation applies.
3. Persistence: add tables ([adding an API resource](adding-an-api-resource.md) steps 1–3). Give independently regenerable things their own id and `status` + `error`.
4. Long-running work: write an idempotent function keyed by entity id and submit it via `get_runner().submit(name, fn, ...)` ([workflow architecture](../architecture/workflow-architecture.md)). Persist failures on the entity.
5. LLM use goes through `intelligence.registry` and a task-specific model setting (add `<task>_llm_model` to `Settings` and `.env.example`; `Settings.model_for(task)` already resolves `analysis|story|script|classification`).
6. Tests next to the behaviour; add docs under `docs/domains/` and update [status](../reference/status.md).

## Rules

- No cross-module reach-ins to provider SDKs; no HTTP clients outside `intelligence/` and provider classes.
- No deployment split until justified ([ADR-006](../decisions/ADR-006-modular-monolith.md)).
- Do not add speculative fields or abstractions without a consumer.

> Working as an AI coding agent? Read [AI agent guide](ai-agent-guide.md) first.
