# Frontend Testing

> Vitest unit tests for the web app. (UI architecture: [frontend docs](../frontend/frontend-testing.md).)

## Status

Implemented, minimal.

## Setup

`apps/web/vitest.config.ts`: jsdom, React plugin, alias `@` → `src`, setup file loads `@testing-library/jest-dom`. Include pattern `src/**/*.test.{ts,tsx}`. Run: `pnpm --filter @storyweaver/web test` (or `make test-web`).

## Covered

(Counts: [testing strategy](testing-strategy.md#layers).)


- `StatusBadge` renders known and unknown statuses.
- `ErrorState` is announced with `role="alert"`; `EmptyState` shows its hint.
- `api()` returns JSON, wraps non-2xx in `ApiError` (with `status`, `code`, the server's `detail`, joined FastAPI validation messages), omits `Content-Type` for `FormData`, and gives a helpful "Is it running?" message when `fetch` rejects.
- Source Library (P1): typed endpoint helpers; the safe `<mark>` snippet renderer including hostile-markup cases (`<script>`, `<img onerror>`, nested/stray tags stay text, entities decoded once); the run-polling hook (stops at a terminal state, refreshes the source queries); the add dialog (client checks for extension/size/empty/title, `FormData`, duplicate notice, 413/422/409 messages, attach mode without title or URL tab, following a run to completion); the list and search views (statuses, retry, searchable badge, usage); the source detail page (failure panel, attach action, delete with confirm and the `source_in_use` message); project source links.

## Not covered

`ResourceList` loading/error/empty/table states with a `QueryClientProvider`, the projects create form mutation, visual layout of the Source Library pages (checked by hand once against real data, not by a test), `AppShell` active-link logic, Zustand sidebar store, Studio page (needs Remotion Player in jsdom — prefer E2E).

## Guidance

Mock `fetch` with `vi.stubGlobal`; wrap queries in a fresh `QueryClient` per test; prefer role/text queries. Type safety (`pnpm typecheck`) and ESLint are part of the same gate ([quality gates](quality-gates.md)).
