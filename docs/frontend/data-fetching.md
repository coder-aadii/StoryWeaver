# Frontend Data Fetching

> How the web app calls the API and handles errors.

## Status

**Implemented.**

## Client

`src/lib/api.ts` exports `api<T>(path, init?)`:

- Base URL: `NEXT_PUBLIC_API_URL ?? "http://localhost:8000"`, prefix `/api/v1`. The variable is read from `apps/web/.env.local` or the shell, **not** from the repository-root `.env` ([KI-21](../reference/status.md#known-issues-and-limitations)).
- Sends `Content-Type: application/json`; returns `undefined` for `204`.
- Network failure → `ApiError(0, "Cannot reach the API at … Is it running?")`.
- Non-2xx → `ApiError(status, "<status> <statusText>")`. The response body (FastAPI's `detail`, validation errors) is **not** parsed yet; improving this is a known gap.
- No auth headers (the API has no authentication — [../api/authentication.md](../api/authentication.md)).

Browser calls rely on API CORS: allowed origins default to `http://localhost:3000` and `http://localhost:3100` (`CORS_ORIGINS` setting).

## Query conventions

- Key = API path for list resources (`["/projects"]`), `["/projects", id]` for detail, `["ready"]`, `["providers"]` for health.
- `ResourceList` encapsulates loading (skeleton rows, `aria-busy`), error (`role="alert"`), empty and table states.
- Mutations use `useMutation` and invalidate by key (see project creation).

## Types

Hand-written TypeScript interfaces mirror API read models. They can drift from the backend; generating them from `/openapi.json` is *Decision pending*. Timeline types are separate (zod in `@storyweaver/video`, mirroring Pydantic `Timeline`; see [../media/timeline-specification.md](../media/timeline-specification.md)).

## Pagination

Lists call the endpoint without `limit/offset`, so they get the default 50 newest items. No paging UI or total count exists. See [../api/pagination.md](../api/pagination.md).

## Failure modes

API down → red "API not ready" badge, error states on pages, dashboard banner. API up but DB down → `/health/ready` returns 503, same UI. Stale cache for ≤10 s after external changes.

## Target

Typed client generation, `detail` message parsing, request cancellation, polling for workflow status ([../workflows/workflow-overview.md](../workflows/workflow-overview.md)). Planned — not implemented.
