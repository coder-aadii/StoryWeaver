# End-to-End Testing

> Playwright tests against the running dev stack.

## Status

Implemented, small (counts: [testing strategy](testing-strategy.md#layers)).

## Setup

`apps/web/playwright.config.ts`: `testDir ./e2e`, base URL `http://localhost:3100`, `webServer` runs `pnpm dev` (reuses an existing server). It does **not** start the API or database — start them first ([setup](../development/setup.md)).

```bash
make e2e
```

Browser: normally `pnpm --filter @storyweaver/web exec playwright install chromium`. Playwright does not support Ubuntu 20.04; set `PLAYWRIGHT_CHROMIUM_PATH` to any Chromium binary (on the dev machine, Remotion's `chrome-headless-shell` under `packages/video/node_modules/.remotion/` worked).

## Covered

`e2e/sources.spec.ts` (P1): through the real UI and API, upload a transcript → it appears once → a keyword search finds it → uploading the same words again shows "already in your library". It uses the **upload path only** (no network, no yt-dlp) with a unique word per run so reruns do not collide. Precondition: the API running against a **disposable** database with the P1 migration applied (never a hosted one). Verified on the dev machine with the local Docker-free Postgres.

`e2e/navigation.spec.ts`:

1. `/` redirects to `/dashboard`; sidebar navigation to Projects works.
2. `/studio` shows the Studio heading and the "Render path" card.

## Not covered

Creating a project through the UI, error states when the API is down, Player playback, responsive layout. Test data is not isolated: tests run against whatever database the API uses — do not point them at data you care about. The `pnpm dev` web server they start binds to `127.0.0.1`.
