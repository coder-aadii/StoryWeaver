# Local Storage Security

> Protecting the `data/` directory and metadata store.

## Status

Partially implemented. Path safety is implemented and **in use** (raw transcripts, P1); permissions/encryption are not.

## Implemented

`LocalStorage` (`core/storage.py`) maps logical keys such as `images/<id>.png` to files under `STORAGE_ROOT` (default `<repo>/data` when the variable is unset **or empty**; a relative value resolves against the repository root — previously KI-1, resolved in P0). Nothing in the API calls `LocalStorage` yet ([KI-9](../reference/status.md#known-issues-and-limitations)). `path_for` rejects empty, absolute, backslash-leading and NUL-containing keys, resolves the path, and requires it to remain inside the root and not equal the root. Symlinks are resolved before the check, so a symlink escaping the root is refused. `exists`/`open`/`delete`/`put` all go through it. `put` streams to a `.part` file, enforces `MAX_UPLOAD_BYTES` and raises the typed `FileTooLargeError` (mapped to HTTP 413) on overflow, removing the partial file. The database stores only `storage_key` strings, never absolute paths.

## Rules for callers

- Build keys from internal ids and server-chosen extensions; pass any user-provided name through `sanitize_filename` first.
- Do not accept raw paths from API clients; accept asset ids and look up `storage_key`.
- Never serve `data/` directly via a static file server without per-asset authorisation.

## Not implemented / gaps

File permissions hardening (relies on the OS user/umask), encryption at rest, quota per project, orphan cleanup ([data lifecycle](../data/data-lifecycle.md)), `delete` of a key that is a directory (only files are unlinked), TOCTOU hardening between `path_for` and open (acceptable for single-user local use). Object storage (MinIO/S3) is Planned; its access policy is Decision pending. Layout: [storage layout](../data/storage-layout.md). Related: [file security](file-security.md).
