# End-to-End Testing

> Playwright tests against the running dev stack.

## Status

Implemented, minimal (counts: [testing strategy](testing-strategy.md#layers)).

## Setup

`apps/web/playwright.config.ts`: `testDir ./e2e`, base URL `http://localhost:3100`, `webServer` runs `pnpm dev` (reuses an existing server). It does **not** start the API or database — start them first ([setup](../development/setup.md)).

```bash
make e2e
```

Browser: normally `pnpm --filter @storyweaver/web exec playwright install chromium`. Playwright does not support Ubuntu 20.04; set `PLAYWRIGHT_CHROMIUM_PATH` to any Chromium binary (on the dev machine, Remotion's `chrome-headless-shell` under `packages/video/node_modules/.remotion/` worked).

## Covered (`e2e/navigation.spec.ts`)

1. `/` redirects to `/dashboard`; sidebar navigation to Projects works.
2. `/studio` shows the Studio heading and the "Render path" card.

## Not covered

Creating a project through the UI, error states when the API is down, Player playback, responsive layout. Test data is not isolated: tests run against whatever database the API uses — do not point them at data you care about. The `pnpm dev` web server they start binds beyond localhost ([KI-20](../reference/status.md#known-issues-and-limitations)).
