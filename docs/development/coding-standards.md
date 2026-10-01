# Coding Standards

> Conventions enforced by tooling and those enforced by review.

## Status

Implemented (tooling); conventions are by review.

## Python (`apps/api`)

- Python ≥ 3.12 (`enum.StrEnum`, `datetime.UTC`, `X | None` syntax). Line length 100 (`ruff format`).
- Ruff rules: `E,F,I,UP,B,SIM`; `E501` ignored because the formatter owns line length. FastAPI `Depends`/`Query` are registered as immutable calls for `B008`.
- Pyright runs in **strict** mode with these relaxed: `reportMissingTypeStubs`, `reportMissingModuleSource`, `reportUnknownMemberType`, `reportUnknownVariableType`, `reportUnknownArgumentType`, `reportUnknownParameterType`, `reportUnknownLambdaType`, `reportMissingParameterType`, `reportUntypedFunctionDecorator` (authoritative list: `[tool.pyright]` in `apps/api/pyproject.toml`). Alembic is excluded.
- Settings only via `get_settings()`; never read `os.environ` in business code. Model names come from settings, never literals.
- Never log secrets; `core/logging.py` masks keys whose final word is a secret word (`api_key`, `password`, `authorization`, `token`/`access_token`, …) and scrubs secret-shaped substrings in every string, including exception text (previously KI-2, resolved in P0). It is best-effort, so still avoid passing secrets into messages, and never log prompts or request bodies at INFO.
- Raise the typed errors in `core/errors.py` (`ProviderNotConfiguredError`, `ProviderError`, `UnsafePathError`, `InvalidSourceError`).
- No `subprocess` with user-controlled strings; use library APIs (yt-dlp Python API) or argument lists.
- Lazy imports for heavy optional dependencies (`yt_dlp`, `faster_whisper`).

## TypeScript

- Both packages use `strict: true`; avoid `any`.
- **`apps/web`** has ESLint (`eslint-config-next`) and Prettier (width 100, tailwind plugin; `src/components/ui`, which is shadcn-generated, is excluded from Prettier).
- **`packages/video`** has **neither** ESLint nor Prettier — only strict `tsc` (`pnpm --filter @storyweaver/video typecheck`) and Vitest. `make lint`/`make format` do not format it.
- Client components only where needed (`"use client"` pages that pass functions to `ResourceList`).
- Data via TanStack Query; UI state in Zustand ([state management](../frontend/state-management.md)).

## Commits

**Do not commit or push unless explicitly requested by the user** (this applies to humans directing an agent and to agents alike; see the [AI agent guide](ai-agent-guide.md)). When a commit is requested: imperative subject line, no secrets, no generated media, no `.env`. History policy (rewrites, force-push) is the owner's decision and needs explicit instruction.

## Not enforced today

No import-linter, no docstring checks, no coverage threshold ([quality gates](../testing/quality-gates.md)).

> Working as an AI coding agent? Read [AI agent guide](ai-agent-guide.md) first.
