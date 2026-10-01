# API Testing

> HTTP-level tests with FastAPI's `TestClient`.

## Status

Implemented for the generic CRUD behaviour; thin coverage across the 10 resources.

## Covered (`apps/api/tests/test_api.py`)

- Project create → patch status → list → delete → 404.
- Invalid enum value → 422.
- Duplicate `(platform, external_id)` source → 409.
- Foreign key to a non-existent project (scene) → 409, not 500.

Health tests: [unit testing](unit-testing.md), [integration testing](integration-testing.md).

## Not covered

Per-resource create/patch for channels, transcripts, topics (slug pattern), collections, scripts, assets, renders; pagination bounds (`limit` 1–200, `offset` ≥ 0 → 422 outside); unknown-field rejection on PATCH (`extra="forbid"`), explicit `null` on PATCH (clears nullable columns, 422 on NOT NULL fields), over-long values on update schemas (422), URL validation on source/channel create, the `{detail, code}` error bodies and the domain-error → HTTP mapping (`tests/test_api_hardening.py`; previously KI-4/KI-8/KI-12). The generic factory means one well-tested path protects most routes, but resource-specific validators (e.g. topic slug regex) deserve cases.

## Approach

Test behaviour via the public contract in [API conventions](../api/API-conventions.md) and [errors](../api/errors.md). Use the OpenAPI schema (`/openapi.json`, the current set of paths) for contract diffing — Decision pending whether to snapshot it.
