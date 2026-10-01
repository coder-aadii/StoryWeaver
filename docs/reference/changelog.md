# Changelog

> Notable changes to the project and its documentation, newest first.

## Status

Implemented (maintained manually).

## Unreleased

- Added the full documentation system under `docs/` (171 files), then applied an audit pass: corrected factual errors, added the canonical [known issues](status.md#known-issues-and-limitations) list, requirements/glossary/status entries, and consolidated duplicated explanations. No code changed.

- Added [external resources](external-resources.md): ~65 reviewed third-party GitHub repos by need (images, voice, video/editor, source/intelligence, provider lists) with licences and cautions — reference only, none adopted.

- P0-T6/T7: Python↔zod timeline contract test (canonical samples in `packages/schemas/samples`), render asset-path spike (`Assets` composition, fixture render verified) and [ADR-009](../decisions/ADR-009-render-asset-resolution.md).

## 2026-10-01 — P0 foundation hardening

Code fixes (see [known issues](status.md#known-issues-and-limitations) for history; tests: pytest 232 with a database, Vitest 21, Playwright 2):

- **Configuration:** an empty `STORAGE_ROOT` means unset (`<repo>/data`); `.env.example` no longer sets it and lists the optional application variables; `apps/web/.env.example` added for `NEXT_PUBLIC_API_URL`; new settings `LLM_TIMEOUT_SECONDS`, `DB_CONNECT_TIMEOUT_SECONDS` (KI-1, KI-21, KI-26 part).
- **Logging:** redaction masks secret-named keys by final word and scrubs secret-shaped values, so `output_tokens` is logged as a number (KI-2).
- **Providers:** all failures surface as `ProviderError` subclasses (`ProviderTimeoutError`, `ProviderResponseError`); shared mocked-HTTP contract tests for every adapter (KI-3).
- **API:** `null` on required PATCH fields and over-long values are 422; source/channel URLs validated on create; uniform `{detail, code}` error bodies and domain-error → HTTP mapping; `/health/ready` logs failures and has a connect timeout; `LocalStorage` raises the typed `FileTooLargeError` (KI-4, KI-5, KI-8, KI-12).
- **Tests:** destructive-database guard (`*_test`, never the application database), session-wide isolation from real configuration, migration up/down/up test (KI-11, KI-19).
- **Contracts and rendering:** Python↔zod timeline contract tests over shared samples (KI-7, mitigated); render asset-path spike and [ADR-009](../decisions/ADR-009-render-asset-resolution.md) (KI-17, decision only).
- **Local-only binding:** dev servers bind to `127.0.0.1`; CORS also allows `http://127.0.0.1:3100` (KI-20).

## 2026-10-01 — Initial foundation

- FastAPI backend with 10 CRUD resource groups and health endpoints; PostgreSQL + pgvector schema (17 tables) with Alembic.
- Provider interfaces and adapters (LLM, embeddings, image, voice, transcription, source extraction); local workflow runner; deterministic timeline builder; traversal-safe local storage.
- Next.js app shell; Remotion `Basic` composition with verified sample render.
- Tests (pytest, Vitest, Playwright), linting, Makefile, Docker Compose (unverified), Docker-free Postgres helper.

See [status](status.md) for what is and is not implemented.
