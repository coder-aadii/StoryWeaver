# Storage Layout

> Where files live on disk and how storage keys are validated.

## Status

**Partially implemented.** `LocalStorage` and the `data/` skeleton exist and are unit-tested. No API endpoint uploads files and no workflow writes assets yet. MinIO/S3 is **Future** ([ADR-008](../decisions/ADR-008-storage-strategy.md)).

## Directory layout (implemented skeleton)

```text
data/                  (contents git-ignored; .gitkeep files keep the skeleton)
  sources/  transcripts/  embeddings/  images/  audio/
  music/    sfx/          projects/    renders/ temporary/
```

Root: `STORAGE_ROOT` (default `<repo>/data` **only when the variable is unset**; `.env.example` ships it empty, which resolves to the process working directory — [KI-1](../reference/status.md#known-issues-and-limitations)). Bucket names are listed in `app/core/storage.py` (`BUCKETS`). What each directory *will* hold (none is populated by code today): optional source media (`sources`) — **the source library does not require downloading media**; metadata, transcripts, chunks and embeddings are enough, and downloading is an optional future capability when a workflow genuinely needs it; transcript files (`transcripts`) — if raw transcripts are stored as files, the DB has **no column to record the key** (*Decision pending*, see [source-data-model](source-data-model.md)), exported vectors if ever needed (`embeddings`), per-asset-type media, per-project working files (`projects`), final MP4s (`renders`), scratch (`temporary`). The key naming convention (e.g. `images/<project_id>/<scene_id>/<asset_id>.png`) is *Decision pending*.

The dev Docker-free Postgres helper also keeps its cluster in `data/temporary/pgdata` (ignored).

## `LocalStorage` behaviour (implemented)

- `path_for(key)` resolves under the root and raises `UnsafePathError` for empty keys, leading `/` or `\`, NUL bytes, `..` escapes or the root itself.
- `put(key, stream)` streams in 1 MiB chunks to `<key>.part`, hashes with sha256, enforces `MAX_UPLOAD_BYTES` (default 512 MiB; raises a plain `ValueError`, not a typed error — an endpoint must map it to HTTP 413), then atomically renames. Returns `(size_bytes, sha256)`. Never loads whole files into memory.
- `open`, `exists`, `delete` (idempotent).
- `sanitize_filename` strips directories and unsafe characters, max 200 chars.
- Interface: `Storage` protocol so an S3-compatible implementation can be swapped in.

## Rules

1. DB stores keys, not paths; keys are relative and use `/`.
2. Large media is processed via filesystem intermediates, not RAM ([architecture/scalability](../architecture/scalability.md)).
3. Anything under `data/` is regenerable or user-owned; it is never committed.

## Limitations

No quota, no orphan cleanup, no content-addressed dedup, no signed URLs, no serving endpoint — so neither the Studio Player nor the renderer can fetch a stored file today. `LocalStorage` is used by no route ([KI-9](../reference/status.md#known-issues-and-limitations), [KI-17](../reference/status.md#known-issues-and-limitations)). See [data-lifecycle](data-lifecycle.md), [security/file-security](../security/file-security.md), [operations/backups](../operations/backups.md).
