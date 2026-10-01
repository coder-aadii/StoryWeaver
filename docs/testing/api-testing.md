# API Testing

> HTTP-level tests with FastAPI's `TestClient`.

## Status

Implemented for the generic CRUD behaviour (thin coverage across the plain resources) and **thorough for the Source Library API** (`test_sources_api.py`, P1).

## Covered (`apps/api/tests/test_api.py`)

- Project create → patch status → list → delete → 404.
- Invalid enum value → 422.
- Duplicate `(platform, external_id)` channel → 409 `duplicate` (sources are no longer created through generic CRUD).
- Foreign key to a non-existent project (scene) → 409, not 500.

## Covered — Source Library (`apps/api/tests/test_sources_api.py`, `test_ingestion_service.py`, `test_runs.py`)

Run with `TEST_DATABASE_URL` set (they skip without it). Network is never touched: YouTube is faked by `tests/support.py::FakeYouTube`, which reuses the real pure URL identification and returns canned metadata/captions (modes: ok, no captions, unavailable, transient failure, extractor error, yt-dlp missing); background work runs inline (`InlineRunner`); storage is a temp directory (`storage_root`); the `api` fixture gives each request its own session like production.

- Add by URL: `202` + run completes, second add (any URL form) = `200 already_exists`, channel/playlist/foreign/`file://`/look-alike URLs refused, yt-dlp missing = `409` and nothing created, no-captions fallback via attach, retry after a transient failure, `nothing_to_retry`.
- Add by transcript: TXT/SRT/VTT of the same words = one source (fingerprint), pasted text and VTT sniffing, new version on changed text, validation errors, malformed SRT with line number, oversize `413`, non-UTF-8, hostile filenames never reach the filesystem.
- List filters/pagination, detail/PATCH rules, delete blocked when used, transcript and chunk paging, `/transcripts` read-only (`405`), search (route not shadowed by `/{id}`, highlight + timestamps, HTML-safe snippets, hostile and odd syntax, `exclude_used`, `source_id`), project links (idempotent) and usage, runs, attach refused while an import runs, OpenAPI paths.
- Service level: dedupe, versioning and `is_current`, chunk/raw-file cleanup on failure, startup reconciliation, worker robustness.

Health tests: [unit testing](unit-testing.md), [integration testing](integration-testing.md).

## Not covered

Per-resource create/patch for channels, transcripts, topics (slug pattern), collections, scripts, assets, renders; pagination bounds (`limit` 1–200, `offset` ≥ 0 → 422 outside); unknown-field rejection on PATCH (`extra="forbid"`), explicit `null` on PATCH (clears nullable columns, 422 on NOT NULL fields), over-long values on update schemas (422), URL validation on source/channel create, the `{detail, code}` error bodies and the domain-error → HTTP mapping (`tests/test_api_hardening.py`; previously KI-4/KI-8/KI-12). The generic factory means one well-tested path protects most routes, but resource-specific validators (e.g. topic slug regex) deserve cases.

## Approach

Test behaviour via the public contract in [API conventions](../api/API-conventions.md) and [errors](../api/errors.md). Use the OpenAPI schema (`/openapi.json`, the current set of paths) for contract diffing — Decision pending whether to snapshot it.
