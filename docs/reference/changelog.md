# Changelog

> Notable changes to the project and its documentation, newest first.

## Status

Implemented (maintained manually).

## Unreleased

- Added the full documentation system under `docs/` (171 files), then applied an audit pass: corrected factual errors, added the canonical [known issues](status.md#known-issues-and-limitations) list, requirements/glossary/status entries, and consolidated duplicated explanations. No code changed.

## 2026-10-01 — Initial foundation

- FastAPI backend with 10 CRUD resource groups and health endpoints; PostgreSQL + pgvector schema (17 tables) with Alembic.
- Provider interfaces and adapters (LLM, embeddings, image, voice, transcription, source extraction); local workflow runner; deterministic timeline builder; traversal-safe local storage.
- Next.js app shell; Remotion `Basic` composition with verified sample render.
- Tests (pytest, Vitest, Playwright), linting, Makefile, Docker Compose (unverified), Docker-free Postgres helper.

See [status](status.md) for what is and is not implemented.
