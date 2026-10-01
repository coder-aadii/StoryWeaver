# Repository Structure

> Where things live and why.

## Status

Implemented.

```text
apps/api/            FastAPI application
  app/core/          config.py (Settings), logging.py, errors.py, storage.py
  app/db/            base.py (Base, mixins, naming convention), session.py (lazy engine)
  app/models/        enums.py, domain.py (17 tables)
  app/schemas/       resources.py (API models), scene.py (SceneSpec/Timeline), source.py (NormalizedSource)
  app/api/           crud.py (generic router factory), v1/router.py, v1/health.py
  app/ingestion/     base.py, youtube.py, transcription.py, chunking.py
  app/intelligence/  providers/{base,ollama,openai_compatible,openrouter,grok,google,claude_compatible}.py, registry.py
  app/visual/        base.py (ImageGenerator, MockImageGenerator, ComfyUIProvider stub)
  app/voice/         base.py (VoiceProvider, UnconfiguredVoiceProvider)
  app/video/         timeline.py (deterministic timing)
  app/workflows/     runner.py (LocalRunner)
  app/story/, app/quality/   placeholders (docstring only)
  alembic/           env.py, versions/
  tests/
apps/web/            Next.js App Router UI (src/app, src/components, src/lib), e2e/
packages/video/      Remotion compositions, camera math, sample/timeline.json
packages/schemas/    JSON Schema exported from Pydantic (make schemas)
packages/prompts/, packages/config/   README-only placeholders
services/            intentionally empty
infrastructure/      postgres/init (CREATE EXTENSION vector); temporal, docker, scripts placeholders
scripts/             dev_postgres.py, export_schemas.py
data/                local storage skeleton; contents git-ignored
docs/                this knowledge base
```

## Boundaries

- The monorepo is a pnpm workspace (`apps/web`, `packages/video`) plus a separate uv project in `apps/api`.
- Domain packages inside `apps/api/app/` are modules of **one** deployable ([ADR-006](../decisions/ADR-006-modular-monolith.md)).
- `services/` is where a module would be split out only if it needs independent scaling or a different runtime.
- The Python `Timeline` model is the source of truth; `packages/video/src/types.ts` mirrors it by hand.

## Naming quirk

SQLAlchemy reserves `metadata`, so JSONB `metadata` columns are `meta` attributes in Python.

See also [Backend architecture](../architecture/backend-architecture.md), [Frontend architecture](../architecture/frontend-architecture.md).
