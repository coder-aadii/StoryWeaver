# Assets API

> CRUD for `assets` — metadata records of generated/imported media.

## Status

**Partially implemented.** Metadata CRUD only. **No upload, download or generation endpoint**: files cannot be attached through the API, so `storage_key`, `mime_type`, `size_bytes` and `checksum` are always null for API-created assets (read-only fields).

Base: `/api/v1/assets`

## Create — `POST /assets` → 201
`project_id` (required; unknown → 409), `type` (`image|audio|voice|music|sfx|video|thumbnail|subtitle|reference|render`), optional `scene_id`. Server sets `status=pending`.

## Read model
`id, created_at, updated_at, project_id, scene_id, type, status, storage_key, mime_type, size_bytes, checksum, error`. (`metadata` not exposed.)

## Update — `PATCH /assets/{id}`
Allowed: `status` (`pending|generating|ready|failed`).

## Other
List/get/delete. Deleting a row does not delete the file ([data-lifecycle](../../data/data-lifecycle.md)).

## Planned — not implemented
Multipart upload with size limit and filename sanitisation (primitives exist in `core/storage.py`: [storage-layout](../../data/storage-layout.md)), authenticated file serving, regenerate action.

Related: [asset-data-model](../../data/asset-data-model.md) · [security/file-security](../../security/file-security.md)

Example response (`201`):
```json
{"id":"b3c8…","created_at":"…","updated_at":"…","project_id":"fae5…","scene_id":null,"type":"image","status":"pending",
 "storage_key":null,"mime_type":null,"size_bytes":null,"checksum":null,"error":null}
```
No route serves files from `data/` and `LocalStorage` is not used by any route ([KI-9](../../reference/status.md#known-issues-and-limitations), [KI-17](../../reference/status.md#known-issues-and-limitations)). Asset versioning (e.g. several images for one scene) is not modelled beyond separate `assets` rows ([asset-data-model](../../data/asset-data-model.md)).
