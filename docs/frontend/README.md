# Frontend Documentation

> Entry point for the StoryWeaver web application docs (`apps/web`).

## Status

**Partially implemented.** A working application shell with read-mostly list pages exists. Almost all product UI (import wizards, script/scene editing, asset review, render control) is **Planned — not implemented**. The Studio is a placeholder.

## What exists

Next.js 16 (App Router) · React 19 · TypeScript strict · Tailwind 4 · shadcn/ui · Zustand · TanStack Query · Remotion Player (`Player` from `@remotion/player`; the composition and timeline schema come from the workspace package `@storyweaver/video`). Runs on port **3100** (`pnpm --filter @storyweaver/web dev`). It talks only to the StoryWeaver API at `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`); provider keys never reach the browser.

## Documents

| Doc | Content |
| --- | --- |
| [application-structure.md](application-structure.md) | Directory layout and conventions |
| [routing.md](routing.md) | Route table and page behaviour |
| [state-management.md](state-management.md) | Zustand and server state split |
| [data-fetching.md](data-fetching.md) | API client, query keys, errors |
| [component-architecture.md](component-architecture.md) | Components and composition patterns |
| [design-system.md](design-system.md) | shadcn/ui, tokens, theming |
| [studio.md](studio.md) | The Studio placeholder and target |
| [frontend-testing.md](frontend-testing.md) | Vitest, Playwright |

Related: [../architecture/frontend-architecture.md](../architecture/frontend-architecture.md), [../api/README.md](../api/README.md), [../media/remotion.md](../media/remotion.md).

## Configuration and exposure notes

- `NEXT_PUBLIC_API_URL` must be set in `apps/web/.env.local` (or the shell): Next.js reads env files from `apps/web/`, so the repository-root `.env` does **not** reach the web app ([KI-21](../reference/status.md#known-issues-and-limitations)). It is inlined at build time and is browser-visible, so it must never contain secrets.
- `next dev` binds beyond localhost (it prints a LAN address), so the "do not expose beyond localhost" guidance applies to the web dev server as well as the API ([KI-20](../reference/status.md#known-issues-and-limitations)).
- `next/font/google` downloads fonts at dev/build time, so a first build needs network access ([KI-25](../reference/status.md#known-issues-and-limitations)).
- The API client does not parse FastAPI's `detail`/validation body; UI errors show only `<status> <statusText>` ([data-fetching](data-fetching.md)).

## Current limitations

No authentication, no forms beyond "create project", no mutation of other resources from the UI, no real-time updates (polling only for API status), no accessibility audit, no i18n, no mobile-specific design beyond a horizontally scrolling link bar.
