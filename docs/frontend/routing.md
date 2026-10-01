# Frontend Routing

> Route table and what each page does today.

## Status

**Implemented** for navigation and read views; most pages are **list-only** because creation/import flows are **Planned — not implemented**.

## Routes

| Route | Type | Data (API) | Behaviour today |
| --- | --- | --- | --- |
| `/` | server | — | `redirect("/dashboard")` |
| `/dashboard` | client | `/projects`, `/sources`, `/channels`, `/collections`, `/health/ready` | Four count cards (list length, so capped at the API default page of 50), error banner if API not ready, status note that the pipeline is foundation-only |
| `/sources` | server | — | Cards linking to channels and videos |
| `/sources/channels` | client | `GET /channels` | Table: title, platform, video count, status badge; empty state says import is not implemented |
| `/sources/videos` | client | `GET /sources` | Table: title, platform, duration, status |
| `/topics` | client | `GET /topics` | Table: name, slug, description |
| `/collections` | client | `GET /collections` | Table: name, description |
| `/projects` | client | `GET/POST /projects` | Table + "create project" form (only mutation in the UI) |
| `/projects/[id]` | client | `GET /projects/{id}` | Title, status, created date, error banner, seven "Not implemented yet" stage cards; 404 shown as "Project not found" |
| `/studio` | client | none | Remotion Player on a bundled sample timeline + render-path list ([studio.md](studio.md)) |
| `/settings` | client | `GET /health/providers` | Read-only provider status cards |

Navigation: sidebar (collapsible via Zustand) on `md+`, horizontally scrolling link bar on small screens; active link uses `aria-current="page"`. Page titles use the template `"%s · StoryWeaver"` where a server page exports `metadata` (client pages inherit the default title).

## Notes

- Dynamic route params are read with `useParams` inside a client component, avoiding reliance on server `params` typing.
- Dashboard counts are approximate until list endpoints expose totals ([../api/pagination.md](../api/pagination.md)).

## Planned routes

`/studio` will become the staged production workspace ([studio.md](studio.md)). Other planned routes: source import wizard, channel import chooser (10/25/50/all/custom), transcript viewer, project workspace tabs (analysis, story candidates, script versions, storyboard, assets, renders, QA), library search. Planned — not implemented.
