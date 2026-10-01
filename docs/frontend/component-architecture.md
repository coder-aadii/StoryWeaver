# Frontend Component Architecture

> The existing components, their contracts, and composition rules.

## Status

**Implemented** (small set).

## Components

| Component | File | Responsibility |
| --- | --- | --- |
| `Providers` | `components/providers.tsx` | TanStack `QueryClientProvider` |
| `AppShell` | `components/app-shell.tsx` | Sidebar nav (7 links), top bar with tagline and `ApiStatus`, mobile link bar; reads `useUi` |
| `ApiStatus` | `components/api-status.tsx` | Badge from `/health/ready` (loading / "API not ready" / "API ready"), refetch 15 s |
| `PageHeader` | `components/page-header.tsx` | Title, description, right-aligned actions slot |
| `ResourceList<T>` | `components/resource-list.tsx` | Generic fetch+table: props `path`, `columns: {header, cell}[]`, `emptyTitle`, `emptyHint` |
| `EmptyState`, `ErrorState`, `LoadingRows` | `components/states.tsx` | Shared state presentations |
| `StatusBadge` | `components/status-badge.tsx` | Maps status string to a badge variant (`completed/ready/imported`→default, `failed`→destructive, `draft/pending/discovered/queued`→outline, else secondary) |
| `ui/*` | `components/ui/` | shadcn: badge, button, card, skeleton, table |

## Composition rules

1. Pages compose `PageHeader` + data component; they own no styling beyond layout.
2. Every data view must handle **loading, error and empty** states (use `ResourceList` or `states.tsx`).
3. Status is always displayed through `StatusBadge`, so a new enum value needs only a mapping there. Mapping covers values from all backend status enums, with a neutral fallback.
4. Prefer small presentational components over deep prop drilling; no global component library beyond shadcn.

## Gaps

No forms library, dialogs, toasts, tabs, or data-grid features (sorting, filtering, paging). Add via shadcn when a feature needs them. Accessibility: nav landmarks labelled ("Main", "Mobile"), alerts use `role="alert"`; no formal audit.

## Target components (Planned — not implemented)

Import wizard, transcript viewer with timestamps, story-candidate cards, script version diff, scene board, asset gallery with per-scene regenerate, render progress, QA findings panel. See [studio.md](studio.md).
