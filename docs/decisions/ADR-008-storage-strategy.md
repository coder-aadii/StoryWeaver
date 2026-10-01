# ADR-008: Filesystem storage behind an abstraction

> Binary media lives on disk (later object storage); PostgreSQL stores only metadata and storage keys.

## Status

Accepted · 2026-10-01 · **Partially implemented** — `LocalStorage` exists and is tested; no route or workflow uses it, there is no upload endpoint and nothing serves files over HTTP ([KI-9](../reference/status.md#known-issues-and-limitations)); S3/MinIO is Future.

## Context

Images, audio and video are large; storing them in Postgres would bloat the database and backups. Local development needs zero extra services.

## Decision

- Files live under `data/` (configurable `STORAGE_ROOT`; note the empty `STORAGE_ROOT=` line in `.env.example` makes it resolve to `.` — [KI-1](../reference/status.md#known-issues-and-limitations)) in fixed buckets: `sources, transcripts, embeddings, images, audio, music, sfx, projects, renders, temporary`. Contents are git-ignored; `.gitkeep` files preserve the skeleton.
- Code addresses files by **storage key** (relative path), recorded in `assets.storage_key` with `mime_type`, `size_bytes` and a SHA-256 `checksum`.
- The `Storage` protocol (`put/open/exists/delete`) isolates callers from the backend. `LocalStorage` resolves keys under the root and rejects absolute paths, `..` traversal, NUL bytes and escapes; `put` streams in 1 MiB chunks, enforces `max_upload_bytes` (raising a plain `ValueError`, not a typed error), writes to a `.part` file and renames atomically.
- Intermediate media use filesystem files; large videos are never read fully into RAM.
- MinIO/S3 will implement the same protocol (compose profile exists, unused). Migration path: copy files, keep keys.

## Alternatives considered

Large objects in Postgres (rejected); MinIO from day one (extra mandatory service; rejected for local-first).

## Consequences

- Backups must cover both the database and `data/` ([backups](../operations/backups.md)).
- Filename sanitising (`sanitize_filename`) is available; the key scheme per asset type (project/scene paths, versioning of regenerated assets) is **Decision pending** until asset workflows exist ([storage-layout](../data/storage-layout.md)).
- No content-addressed deduplication yet (checksum is stored, enabling it later).

See [storage-architecture](../architecture/storage-architecture.md), [local-storage-security](../security/local-storage-security.md), [asset-data-model](../data/asset-data-model.md).

## Revisit when

Assets must be shared across machines, total media size outgrows local disk, or content-addressed deduplication becomes worthwhile.
