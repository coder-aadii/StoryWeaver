# Frontend Architecture

> How the Next.js application in `apps/web` is structured.

## Status

**Implemented** as an application shell with read-mostly pages. The Studio is a **placeholder**; the editor is **Future**.

## Purpose

Describe routing, data access, state, components and the relationship with `packages/video`. Detailed docs: [frontend/](../frontend/README.md).

## Current implementation

- **Stack**: Next.js 16 (App Router), React 19, TypeScript strict, Tailwind 4, shadcn/ui primitives (`components/ui`: button, card, badge, table, skeleton), lucide icons, TanStack Query, Zustand.
- **Routes** (`src/app/`): `/` (redirects to `/dashboard`), `/dashboard`, `/sources`, `/sources/channels`, `/sources/videos`, `/topics`, `/collections`, `/projects`, `/projects/[id]`, `/studio`, `/settings`.
- **Shell** (`components/app-shell.tsx`): sidebar + top bar + mobile nav; sidebar collapse state in Zustand (`lib/store.ts`); API readiness badge (`api-status.tsx`).
- **Data access**: `lib/api.ts` — `fetch` wrapper over `${NEXT_PUBLIC_API_URL}/api/v1`, throws `ApiError`. Pages use TanStack Query (`useQuery`, one `useMutation` for creating projects). Query key = resource path (e.g. `["/projects"]`).
- **Shared list view**: `components/resource-list.tsx` renders loading (skeleton), error, empty and table states from a column definition; list pages are client components because they pass render functions.
- **Studio** (`/studio`): embeds `@remotion/player` with `BasicComposition` and the sample timeline from `@storyweaver/video`; a static "render path" panel. No editing.
- **Secrets**: none in the browser; only `NEXT_PUBLIC_API_URL`.

## Target architecture

Same structure, plus: forms and actions for the pipeline (import source, generate script, regenerate scene), per-scene status views, job progress, and a Studio that loads a project's real timeline and assets. Server-sent progress (polling vs SSE) — **Decision pending**.

## Components and responsibilities

| Piece | Responsibility |
| --- | --- |
| `app/*` pages | Compose layout + `ResourceList`/cards |
| `components/states.tsx` | `EmptyState`, `ErrorState` (`role="alert"`), `LoadingRows` |
| `components/status-badge.tsx` | Status → badge variant mapping (unknown statuses fall back to secondary) |
| `lib/api.ts` | HTTP, error normalisation, API response types |
| `packages/video` | Composition + timeline types shared with the Player |

## Data flow

Browser → `api()` → FastAPI. No Next.js server-side data fetching or API routes are used.

## Failure modes

API down → `ErrorState` with the "Cannot reach the API" message; 404 on project detail → "Project not found."; dashboard shows a readiness warning.

## Extension points

Add a page under `src/app/…`, add a nav entry in `app-shell.tsx`, reuse `ResourceList`. See [frontend/component-architecture](../frontend/component-architecture.md).

## Current limitations

- No create/edit UI except "new project"; most lists are read-only and mostly empty.
- Response types in `lib/api.ts` and page files are hand-written, not generated from OpenAPI.
- `/projects/[id]` stage cards are static "Not implemented yet" placeholders.
- Remotion Player shows a license reminder; `acknowledgeRemotionLicense` is deliberately unset (owner's decision).
- Fonts load from Google Fonts at build/dev time (needs network; [KI-25](../reference/status.md#known-issues-and-limitations)).
- `NEXT_PUBLIC_API_URL` must be set in `apps/web/.env.local` (or the shell); the root `.env` does not reach the web app ([KI-21](../reference/status.md#known-issues-and-limitations)). The zod timeline mirror used by the Player is hand-maintained ([KI-7](../reference/status.md#known-issues-and-limitations)); nothing serves `data/` files to the Player ([KI-17](../reference/status.md#known-issues-and-limitations)).

## Future evolution

Generated API client, real project workspace, scene-level regeneration UI, timeline/asset inspector. See [frontend/studio](../frontend/studio.md) and [product/feature-roadmap](../product/feature-roadmap.md).
