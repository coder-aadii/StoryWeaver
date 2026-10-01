# Frontend State Management

> What state lives where, and why.

## Status

**Implemented** (minimal).

## Split

| Kind | Tool | Current use |
| --- | --- | --- |
| Server state (anything from the API) | TanStack Query | All lists, project detail, readiness, provider status |
| Client UI state | Zustand (`src/lib/store.ts`) | `sidebarOpen` + `toggleSidebar` only |
| Form state | React `useState` | Project title input |
| URL state | Next router | Route and `[id]` |

Rule: **never copy server data into Zustand.** Zustand is for ephemeral UI concerns (sidebar, later: studio selection, playhead, panel layout).

## Query client defaults

`Providers` (`src/components/providers.tsx`) creates one `QueryClient` per mounted tree with `staleTime: 10_000` and `retry: 1`. Individual queries override: `ApiStatus` sets `retry: false` and `refetchInterval: 15000`; the project detail query does not retry on 404.

## Invalidation

Creating a project invalidates `["/projects"]`. Since query keys equal API paths for lists, invalidating a list means invalidating its path ([data-fetching.md](data-fetching.md)).

## Target (Planned — not implemented)

- Workflow progress: poll or server-sent events for entity status (assets, renders) with `refetchInterval` conditional on non-terminal status.
- Optimistic updates for small edits (rename, reorder scenes) with rollback.
- Studio store: selected scene, playhead, zoom, undo stack — client-only, persisted via explicit save to the API (Decision pending).
- Persisting UI preferences (sidebar) in `localStorage` — not done today.
