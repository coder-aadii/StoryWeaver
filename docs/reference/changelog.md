# Changelog

> Notable changes to the project and its documentation, newest first.

## Status

Implemented (maintained manually).

## Unreleased

- Added the full documentation system under `docs/` (171 files), then applied an audit pass: corrected factual errors, added the canonical [known issues](status.md#known-issues-and-limitations) list, requirements/glossary/status entries, and consolidated duplicated explanations. No code changed.

- Added [external resources](external-resources.md): ~65 reviewed third-party GitHub repos by need (images, voice, video/editor, source/intelligence, provider lists) with licences and cautions — reference only, none adopted.

- P0-T6/T7: Python↔zod timeline contract test (canonical samples in `packages/schemas/samples`), render asset-path spike (`Assets` composition, fixture render verified) and [ADR-009](../decisions/ADR-009-render-asset-resolution.md).

## 2026-10-01 — P1 Source Library V1

Tests: pytest 505 with a database, Vitest web 87 + video 14, Playwright 3; `make lint`, `next build` clean. Live-verified once with one public YouTube video (manual captions); other paths by recorded fixtures — see the [verification record](status.md#verification-record).

- **Sources:** add a YouTube video (`POST /sources/from-url`, background run, metadata + captions, no media) or a transcript (`POST /sources/from-transcript`, `.txt`/`.srt`/`.vtt` or pasted text); attach/replace a transcript on an existing source; list, search, detail, edit, delete, retry, usage; project ↔ source links; run polling. Raw `POST /sources` and write routes on `/transcripts` were removed (KI-12, KI-13).
- **Ingestion:** `SourceExtractor` gained `identify`, `ensure_available`, `fetch_transcript` and a registry; YouTube captions (manual → automatic, json3 → vtt, HLS auto-caption playlists) with a host allow-list and size cap; parsers, versioned normalizer, content fingerprint, chunks, raw-file storage via `LocalStorage` (KI-9 partly, KI-14, KI-15, KI-23, KI-24).
- **Data:** migration `e39be38b3620` — `source_videos` (`url` nullable, `kind`, `fingerprint`, `thumbnail_url`), `transcripts` (`is_current`, raw key/hash, `normalizer_version`), generated `search_vector` + GIN on `transcript_chunks`, new `workflow_runs` table.
- **Workflows:** persisted runs on `LocalRunner` (`source.add`, `source.fetch_transcript`), one active run per kind and subject, startup reconciliation.
- **Web:** Source Library pages (list/search/add/detail/retry/delete/usage) and linked sources on the project page; safe rendering of search snippets.
- **Config:** `MAX_TRANSCRIPT_BYTES`, `CAPTION_LANGUAGES`; new dependency `python-multipart`; yt-dlp stays the optional `ingestion` extra.
- **Fixed:** the normalizer no longer leaves a stray space where inline caption tags were removed (`volcanoes</c>.` → `volcanoes.`, [KI-27](status.md#known-issues-and-limitations)); `NORMALIZER_VERSION` is now `"2"`.

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
