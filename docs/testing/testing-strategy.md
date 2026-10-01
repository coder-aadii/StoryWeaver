# Testing Strategy

> What is tested, at which layer, and what is deliberately not tested yet.

## Status

Partially implemented. Unit/integration/API/E2E basics exist; media, AI-evaluation and CI do not.

## Layers

> **This table is the only place test counts are kept.** Other testing and development documents link here instead of repeating numbers, so they cannot drift. Counts below were true at the initial foundation commit (2026-10-01); re-count with the commands in the [testing guide](../development/testing.md) when tests change.

| Layer | Tool | Count today | Doc |
| --- | --- | --- | --- |
| Python unit | pytest | 26 run without a DB | [unit](unit-testing.md) |
| DB integration + API | pytest + real PostgreSQL/pgvector | 9 (skipped without `TEST_DATABASE_URL`) | [integration](integration-testing.md), [API](api-testing.md) |
| Web unit | Vitest + Testing Library | 7 | [frontend](frontend-testing.md) |
| Video package | Vitest | 3 | [media](media-testing.md) |
| End-to-end | Playwright | 2 | [E2E](e2e-testing.md) |
| AI output quality | — | 0 | [AI evaluation](ai-evaluation.md) |

## Principles

1. Few meaningful tests over many placeholders.
2. No network, no real model, no GPU in automated tests; providers are tested with fakes or `httpx.MockTransport`.
3. Real migrations run against a real Postgres (no SQLite substitute) because pgvector and JSONB are used.
4. Deterministic code (timeline, chunking, URL classification, storage safety) gets the densest tests; it is where correctness is checkable.
5. Non-determinism (LLM, image output) is evaluated, not asserted ([AI evaluation](ai-evaluation.md)).

## Results to expect

- Without `TEST_DATABASE_URL`: pytest reports the 26 DB-free tests passing and the 9 DB tests **skipped** — a green run that did not exercise the database.
- With it: all 35 pass. `TEST_DATABASE_URL` is **destructive** (downgrade to base, re-migrate, truncate) and unguarded — use a disposable database ([KI-19](../reference/status.md#known-issues-and-limitations)).
- `make test` also runs the web and video Vitest suites; `make e2e` (Playwright) is separate and needs the dev stack.

## Gaps

No CI ([KI-10](../reference/status.md#known-issues-and-limitations)), no coverage measurement, no migration-drift test beyond manual `alembic check`, no Python/zod `Timeline` contract test ([KI-7](../reference/status.md#known-issues-and-limitations)), test-order sensitivity from the cached engine ([KI-11](../reference/status.md#known-issues-and-limitations)), no real-provider smoke tests. Gate definitions: [quality gates](quality-gates.md). Developer how-to: [testing guide](../development/testing.md).
