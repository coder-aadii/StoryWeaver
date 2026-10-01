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
- `api()` returns JSON, wraps non-2xx in `ApiError` with status, and gives a helpful "Is it running?" message when `fetch` rejects.

## Not covered

`ResourceList` loading/error/empty/table states with a `QueryClientProvider`, the projects create form mutation, `AppShell` active-link logic, Zustand sidebar store, Studio page (needs Remotion Player in jsdom — prefer E2E).

## Guidance

Mock `fetch` with `vi.stubGlobal`; wrap queries in a fresh `QueryClient` per test; prefer role/text queries. Type safety (`pnpm typecheck`) and ESLint are part of the same gate ([quality gates](quality-gates.md)).
