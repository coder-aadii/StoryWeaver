# Pagination

> How list endpoints page results.

## Status

**Partially implemented** (limit/offset only).

## Behaviour (implemented)

`GET /api/v1/<resource>?limit=50&offset=0`

| Param | Default | Range |
| --- | --- | --- |
| `limit` | 50 | 1–200 (outside → 422) |
| `offset` | 0 | ≥ 0 |

Order is fixed: `created_at DESC` (newest first). The response is a bare JSON array — **no envelope, no total count, no next link**. Clients detect the end when fewer than `limit` items return. The web app currently fetches the default page without paging UI.

## Limitations

- Offset paging can skip/duplicate rows if data changes between requests.
- No filters (by status, project, parent id) or sort selection: e.g. you cannot list scenes of one project server-side yet. *Planned — not implemented*; `project_id` filters are the likely first addition.
- Ties in `created_at` have no secondary sort key.

## Future

Cursor pagination and a `{items,total}` envelope: *Decision pending*; would be a v2 concern since it changes the response shape ([API-conventions](API-conventions.md)).
