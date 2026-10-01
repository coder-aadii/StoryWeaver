# Frontend Routing

> Route table and what each page does today.

## Status

**Implemented** for navigation, the **Source Library** (add, list, search, detail, retry, usage, delete — P1) and project/source linking; the other pages (channels, topics, collections) are **list-only** because their creation/import flows are **Planned — not implemented**.

## Routes

| Route | Type | Data (API) | Behaviour today |
| --- | --- | --- | --- |
| `/` | server | — | `redirect("/dashboard")` |
| `/dashboard` | client | `/projects`, `/sources`, `/channels`, `/collections`, `/health/ready` | Four count cards (list length, so capped at the API default page of 50), error banner if API not ready, status note that the pipeline is foundation-only |
| `/sources` | server | — | Cards linking to channels (labelled "channel import arrives in a later release") and videos (add, search, usage) |
| `/sources/channels` | client | `GET /channels` | Table: title, platform, video count, status badge; empty state says import is not implemented |
| `/sources/videos` | client | `GET /sources`, `GET /sources/search`, `POST /sources/from-url`, `POST /sources/from-transcript`, `POST /sources/{id}/retry`, `GET /runs/{id}` | The Source Library: list with kind icon, source and transcript status badges, searchable badge, duration, "used in N projects", Retry on failure; keyword search box (snippets rendered as text with only `<mark>` honoured; timestamps `mm:ss`); "hide sources already used" toggle; **Add source** dialog (tabs *YouTube URL* / *Upload or paste*, client checks mirror the server limits, duplicate notice with link, run polling until a terminal state); empty/loading/error states |
| `/sources/videos/[id]` | client | `GET /sources/{id}`, `/transcript`, `/usage`, `GET /sources/search?source_id=`, `POST /sources/{id}/retry`, `POST /sources/{id}/transcript`, `DELETE /sources/{id}`, `PUT /projects/{pid}/sources/{sid}` | Metadata card (thumbnail, channel, duration, language), failure panel (error code, Retry, **Upload transcript instead** = attach mode), paged transcript viewer (timestamps when timed), in-source search, usage list, *Add to project*, Delete with confirm (409 `source_in_use` → "unlink it from its projects first") |
| `/topics` | client | `GET /topics` | Table: name, slug, description |
| `/collections` | client | `GET /collections` | Table: name, description |
| `/projects` | client | `GET/POST /projects` | Table + "create project" form (only mutation in the UI) |
| `/projects/[id]` | client | `GET /projects/{id}`, `GET/PUT/DELETE /projects/{id}/sources…` | Title, status, created date, error banner, **linked sources with add/remove**, seven "Not implemented yet" stage cards; 404 shown as "Project not found" |
| `/studio` | client | none | Remotion Player on a bundled sample timeline + render-path list ([studio.md](studio.md)) |
| `/settings` | client | `GET /health/providers` | Read-only provider status cards |

Navigation: sidebar (collapsible via Zustand) on `md+`, horizontally scrolling link bar on small screens; active link uses `aria-current="page"`. Page titles use the template `"%s · StoryWeaver"` where a server page exports `metadata` (client pages inherit the default title).

## Notes

- Dynamic route params are read with `useParams` inside a client component, avoiding reliance on server `params` typing.
- Dashboard counts use the list length, or `total` for paged endpoints such as `/sources`; the rest are approximate until their list endpoints expose totals ([../api/pagination.md](../api/pagination.md)).

## Planned routes

`/studio` will become the staged production workspace ([studio.md](studio.md)). Other planned routes: channel import chooser (10/25/50/all/custom), project workspace tabs (analysis, story candidates, script versions, storyboard, assets, renders, QA), library search. Planned — not implemented.
