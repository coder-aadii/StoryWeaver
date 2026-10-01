# Storage Layout

> Where files live on disk and how storage keys are validated.

## Status

**Partially implemented.** `LocalStorage` and the `data/` skeleton exist and are unit-tested. **Only raw transcripts are written today** (P1, `transcripts/<source_id>/v<n>/raw.<ext>`, by the ingestion service through transcript upload/attach and caption fetch); no image/audio/video upload, no workflow writes assets, and nothing serves files yet. MinIO/S3 is **Future** ([ADR-008](../decisions/ADR-008-storage-strategy.md)).

## Directory layout (implemented skeleton)

```text
data/                  (contents git-ignored; .gitkeep files keep the skeleton)
  sources/  transcripts/  embeddings/  images/  audio/
  music/    sfx/          projects/    renders/ temporary/
```

Root: `STORAGE_ROOT` (default `<repo>/data` when unset or empty; relative values resolve against the repository root). Bucket names are listed in `app/core/storage.py` (`BUCKETS`). What each directory holds: **`transcripts`** — raw transcript/caption files exactly as received, `transcripts/<source_id>/v<n>/raw.<ext>`, the only directory populated by code today (the key is recorded in `transcripts.raw_storage_key`, with `raw_sha256`; see [source-data-model](source-data-model.md)). The rest are reserved: optional source media (`sources`) — **the source library does not require downloading media** and stores none; downloading is an optional future capability when a workflow genuinely needs it; exported vectors if ever needed (`embeddings`), per-asset-type media, per-project working files (`projects`), final MP4s (`renders`), scratch (`temporary`). The key naming convention (e.g. `images/<project_id>/<scene_id>/<asset_id>.png`) is *Decision pending*.

The dev Docker-free Postgres helper also keeps its cluster in `data/temporary/pgdata` (ignored).

## `LocalStorage` behaviour (implemented)

- `path_for(key)` resolves under the root and raises `UnsafePathError` for empty keys, leading `/` or `\`, NUL bytes, `..` escapes or the root itself.
- `put(key, stream)` streams in 1 MiB chunks to `<key>.part`, hashes with sha256, enforces `MAX_UPLOAD_BYTES` (default 512 MiB; raises the typed `FileTooLargeError`, which the API maps to HTTP 413; the partial file is removed), then atomically renames. Returns `(size_bytes, sha256)`. Never loads whole files into memory.
- `open`, `exists`, `delete` (idempotent).
- `sanitize_filename` strips directories and unsafe characters, max 200 chars.
- Interface: `Storage` protocol so an S3-compatible implementation can be swapped in.

## Rules

1. DB stores keys, not paths; keys are relative and use `/`.
2. Large media is processed via filesystem intermediates, not RAM ([architecture/scalability](../architecture/scalability.md)).
3. Anything under `data/` is regenerable or user-owned; it is never committed.

## Limitations

No quota, no orphan cleanup, no content-addressed dedup, no signed URLs, no serving endpoint — so neither the Studio Player nor the renderer can fetch a stored file today. `LocalStorage` is used by the transcript ingestion only ([KI-9](../reference/status.md#known-issues-and-limitations), partly resolved in P1; [KI-17](../reference/status.md#known-issues-and-limitations)); deleting a source removes its raw files, and a failed ingest removes the file it just wrote, but there is still no orphan sweep for other causes. See [data-lifecycle](data-lifecycle.md), [security/file-security](../security/file-security.md), [operations/backups](../operations/backups.md).
