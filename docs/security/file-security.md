# File Security

> Rules for uploaded, downloaded and generated files.

## Status

Partially implemented. Primitives exist; **no upload or download endpoint exists**, so these controls are not yet reachable from the API.

## Implemented primitives

- `sanitize_filename`: strips directories (both separators), leading dots/spaces, replaces anything outside `[A-Za-z0-9._-]`, truncates to 200 chars, rejects empty results.
- `LocalStorage.put`: streamed, sha256 computed while writing, hard stop above `MAX_UPLOAD_BYTES` (default 512 MiB), written to `.part` then atomically renamed, `.part` removed on failure. Over the cap it raises a plain `ValueError` (not a typed `StoryWeaverError`), so **any endpoint that uses it must catch it and return HTTP 413**; typed errors are not mapped to HTTP statuses either ([KI-8](../reference/status.md#known-issues-and-limitations), [KI-9](../reference/status.md#known-issues-and-limitations)).
- `assets` rows carry `mime_type`, `size_bytes`, `checksum`, `status`, `error`.

No route uses `LocalStorage` and no endpoint serves files from `data/` today ([KI-9](../reference/status.md#known-issues-and-limitations)).

## Rules for future endpoints (Planned)

1. Accept uploads only through a size-capped streaming path; never `await file.read()` whole videos.
2. Allow-list extensions and sniff content type server-side (do not trust the client `Content-Type`); reject on mismatch.
3. Generate the storage key server-side from ids; keep the original name only as sanitised metadata.
4. Parse subtitle/transcript formats with bounded effort; treat content as text, never markup.
5. Serve files only via an authorised handler with `Content-Disposition` and correct type; never execute or render user-supplied HTML/SVG inline.
6. Run any FFmpeg/ffprobe invocation with argument lists (no shell) on files inside `STORAGE_ROOT`; apply timeouts. Media codecs have a history of vulnerabilities — keep FFmpeg updated.

## Generated media

Images, audio and renders are derived data stored under `data/`; they inherit the project's sensitivity. Checksums enable integrity checks and dedup ([asset data model](../data/asset-data-model.md)). Copyright/similarity: no guarantees are made ([content policy](../product/content-policy-and-source-usage.md)).

See also [local storage security](local-storage-security.md), [input validation](input-validation.md).
