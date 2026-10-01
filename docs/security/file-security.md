# File Security

> Rules for uploaded, downloaded and generated files.

## Status

**Partially implemented.** The controls are live for **transcript uploads and caption downloads** (P1, 2026-10-01): `POST /sources/from-transcript`, `POST /sources/{id}/transcript` and the YouTube caption fetch. There is still **no endpoint that serves files from `data/`** and no upload endpoint for images, audio or video.

## Implemented primitives

- `sanitize_filename`: strips directories (both separators), leading dots/spaces, replaces anything outside `[A-Za-z0-9._-]`, truncates to 200 chars, rejects empty results.
- `LocalStorage.put`: streamed, sha256 computed while writing, hard stop above `MAX_UPLOAD_BYTES` (default 512 MiB), written to `.part` then atomically renamed, `.part` removed on failure. Over the cap it raises the typed `FileTooLargeError` (a `StoryWeaverError` and a `ValueError`), which the API maps to HTTP 413 `file_too_large` (previously a plain `ValueError`; resolved in P0). `put` is used by the ingestion service to store raw transcripts (and its size cap is also enforced earlier by the parser against `MAX_TRANSCRIPT_BYTES`).
- `assets` rows carry `mime_type`, `size_bytes`, `checksum`, `status`, `error`.

`LocalStorage` is now used by the ingestion service (raw transcripts; deletion on source delete or on failure). No endpoint serves files from `data/` today ([KI-9](../reference/status.md#known-issues-and-limitations), [KI-17](../reference/status.md#known-issues-and-limitations)).

## Implemented controls — transcript upload and caption download (P1)

| Control | Where |
| --- | --- |
| Extension allow-list `txt`/`srt`/`vtt` (anything else → `422 unsupported_file_type`); pasted text is sniffed for VTT/SRT | `api/v1/sources.py` |
| The client filename is passed through `sanitize_filename` for validation only and is **never used as a path**: files are stored as `transcripts/<source_id>/v<n>/raw.<ext>` from server-generated ids | `ingestion/service.py` |
| Size cap `MAX_TRANSCRIPT_BYTES` (default 5 MB): the upload is read with a bounded read (cap + 1) and refused with `413 file_too_large`; the caption download is streamed with the same hard cap | routes, `parse_transcript`, `youtube.py` |
| Strict UTF-8 (BOM tolerated); empty input, malformed cues and oversize paragraphs are rejected with a line number where possible; segment count and line length are bounded | `ingestion/parsers.py` |
| Content is treated as text: caption markup is stripped by the normalizer, search snippets are HTML-escaped by the server and rendered as text by the web app (only `<mark>` is honoured) | `normalize.py`, `queries.safe_snippet`, `safe-snippet.tsx` |
| `reference_url` must be `http(s)`, is stored as text, and is never fetched | `api/v1/sources.py` |
| Caption fetch (SSRF guard): `https` only, no credentials, standard port, host must be `youtube.com` or `googlevideo.com` (or a subdomain), checked on every redirect and on every segment of an automatic-caption playlist; redirects to any non-allow-listed host refused; `skip_download` is forced so no media is ever fetched | `ingestion/youtube.py` |
| On failure the raw file is removed and the database transaction rolled back; deleting a source removes its raw files | `ingestion/service.py` |

Tests: traversal-style filenames (`../../etc/passwd.txt`, `..\\..\\evil.txt`), oversize, non-UTF-8, foreign-host and look-alike URLs, caption hosts and redirects, hostile snippet markup — all offline ([API testing](../testing/api-testing.md)).

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
