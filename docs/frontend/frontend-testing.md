# Frontend Testing

> What is tested in `apps/web` and how to run it.

## Status

**Partially implemented.** A small number of meaningful tests exist; coverage of pages is minimal by design.

## Unit/component tests (Vitest)

Config: `vitest.config.ts` (jsdom, React plugin, `@` alias, setup file loading `@testing-library/jest-dom`). Run: `make test-web` or `pnpm --filter @storyweaver/web test`.

| File | Covers |
| --- | --- |
| `src/components/status-badge.test.tsx` | Badge text and fallback; `ErrorState` has `role="alert"`; `EmptyState` hint |
| `src/lib/api.test.ts` | JSON parsing, `ApiError` status on non-2xx, helpful network-failure message |

Current test counts are kept in one place: [testing-strategy](../testing/testing-strategy.md). The `@storyweaver/video` package has its own Vitest suite (camera end points/clamping and sample-timeline schema validation; see [camera-motion](../media/camera-motion.md)).

## End-to-end (Playwright)

`e2e/navigation.spec.ts`: redirect `/` → `/dashboard`, sidebar navigation to Projects, and `/studio` rendering. `playwright.config.ts` starts `pnpm dev` (port 3100, reuses an existing server). The tests only check UI shell and do not require API data, though the API status badge will show "not ready" without a backend.

Browser: Playwright's bundled Chromium is unsupported on Ubuntu 20.04, so set `PLAYWRIGHT_CHROMIUM_PATH` to any Chromium (for example Remotion's headless shell) — see [../development/setup.md](../development/setup.md). On supported systems run `pnpm --filter @storyweaver/web exec playwright install chromium` once.

## Static checks

`pnpm lint` (ESLint), `pnpm typecheck` (strict TS), `pnpm format:check`.

## Gaps and plans

No tests for `ResourceList` states, project creation flow, dashboard counts or settings page; no API-mocked e2e (MSW or Playwright route mocking — *Decision pending*); no visual regression; no accessibility checks (e.g. axe). Add tests alongside each new feature. Strategy overview: [../testing/frontend-testing.md](../testing/frontend-testing.md), [../testing/e2e-testing.md](../testing/e2e-testing.md), [../testing/testing-strategy.md](../testing/testing-strategy.md).
