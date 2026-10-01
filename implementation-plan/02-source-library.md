# P1 — Source Library V1

> Execution plan for the first product milestone: add a single source (YouTube URL or a transcript), store its metadata and transcript once, and make it searchable and reusable — with no model calls and no media download.

## Status

Planned. **Current state of the capability** (verified in the code, 2026-10): *Partially implemented* — schema (`channels`, `source_videos`, `transcripts`, `transcript_chunks`, `project_sources`), `classify_youtube_url`, a metadata-only yt-dlp extractor, `chunk_segments`, a `Transcriber` interface and generic CRUD for sources/transcripts exist. No ingestion code is reachable from any route, no transcript is ever produced, nothing is searchable. Canonical status: [`docs/reference/status.md`](../docs/reference/status.md).

Phase **P1**, Checkpoint **B** ([master plan](IMPLEMENTATION_PLAN.md)). Design lives in [source library](../docs/domains/source-library.md), [ingestion workflow](../docs/workflows/ingestion-workflow.md), [transcript workflow](../docs/workflows/transcript-workflow.md); this file only says *what to build and how to verify it*.

---

## 1. Goal

A user can, from the UI or API:

1. Add a **YouTube video URL** → metadata and captions are fetched (no media download) → a normalized transcript is stored → chunks are stored → the source is **searchable** by keyword.
2. Add a **transcript** (upload `.txt` / `.srt` / `.vtt`, or paste text) with no remote origin → same result.
3. Re-adding the same source is a **no-op** that returns the existing one (dedupe).
4. See why a source failed (no captions, video unavailable, extractor missing) and **retry** or fall back to upload.
5. Search across all sources, see where each hit sits (timestamp), and see **which projects already use a source**.

"Searchable" and "reusable" have these exact meanings here (consistent with [`docs`](../docs/workflows/ingestion-workflow.md)): `SourceVideo.status = imported` means *metadata stored*; **searchable ⇔ the current transcript is `ready` and has ≥ 1 chunk** (derived, never stored as a flag). Reusable ⇔ a project can link it through `project_sources` and the link is queryable.

## 2. Why now

It is the only phase that needs **no AI, no GPU, no cost, and no external service in tests**, yet it produces the input every later stage consumes (P3 reads the current transcript's chunks). It also forces the first real use of the pieces that were built but never wired — `LocalStorage` (KI-9), `LocalRunner`, the extractor, `chunk_segments` — so their defects surface now, cheaply. Channel scanning/embeddings are deliberately **not** here: a single-source library proves the value and fits the 16 GB CPU-only machine ([sequencing rationale](IMPLEMENTATION_PLAN.md#5-dependency-and-order-strategy)).

## 3. Prerequisites

- **P0 complete** ([`01-foundation.md`](01-foundation.md)); specifically these must be closed before the tasks that depend on them:
  - **KI-1** `STORAGE_ROOT` empty-value resolution — needed before **P1-T6** writes raw transcripts. *Blocking.*
  - **KI-8** `StoryWeaverError` → HTTP mapping — needed by **P1-T9/T10** (`ProviderNotConfiguredError` for missing yt-dlp must return an actionable 503, `UnsafePathError`/`InvalidSourceError` must return 4xx). *Blocking unless P1-T1 adds it* (see below).
  - **KI-19/KI-11** test-DB guard and engine-cache isolation — needed before adding DB-heavy tests. *Should fix before.*
  - **KI-4** PATCH validation — the new `SourceVideoUpdate` is written validated (P1-T4); the generic fix is P0's.
- Optional extra installed for the URL path: `cd apps/api && uv sync --extra ingestion` (yt-dlp). Tests must **not** require it (they use recorded fixtures and a fake extractor).
- New dependency: `python-multipart` (FastAPI form/file upload) — **NEW dependency**, add to `apps/api/pyproject.toml` in P1-T9 and note it in the changelog.

## 4. Decisions this phase relies on

| Decision | Applied how |
| --- | --- |
| **D1** job state | P1 creates the **full `workflow_runs` table** (the D1 columns) in its migration and a thin `RunService` (create / mark running / succeeded / failed / list by subject). It runs `source.add` and `source.fetch_transcript` on the existing `LocalRunner`. **P2 generalizes** (startup reconciliation, progress, generic retry endpoint, routing) without a second migration of this table. *Why not purely synchronous:* a yt-dlp call can take seconds and fail transiently; making it a persisted run from day one gives the UI a pollable status and retry now. *Why not the whole P2 runtime:* routing/cache/usage are AI concerns not needed here. |
| **D5** source identity | `url` nullable, new `kind`, `fingerprint`, `thumbnail_url`; uploads use `platform='upload'`, `external_id = sha256` (see 5.2). Fixes KI-14, KI-23 (thumbnail). |
| **D6** transcript storage | Raw bytes via `LocalStorage` (`raw_storage_key`), cleaned `text` + `segments` in DB, `normalizer_version`, `is_current`; versions created **by a service**, never from an API payload. Fixes KI-13. |
| **D7** search | Postgres full-text on `transcript_chunks`. No embeddings (D8 → P11). |
| **D14** auth | None; localhost only. |

### Decision points specific to P1 (recommended default → alternative)

1. **Remove the raw create/patch routes for sources and transcripts** (recommended) — they bypass validation (KI-12) and version rules (KI-13). Replace with the service-backed routes below; update the tests that use them. *Alternative:* keep them with validation bolted on (rejected: two ways to create a source).
2. **FTS text-search config:** `'simple'` (recommended: language-neutral, no stemming, works for any caption language) vs `'english'`. Revisit when non-English usage is real.
3. **Untimed transcripts** (plain `.txt`): make `TranscriptSegment.start/end` optional (recommended; `transcript_chunks.start_seconds/end_seconds` are already nullable) vs fabricating timestamps (rejected: misleading). Consequence: `chunk_segments` must tolerate `None`.
4. **Exact vs near duplicates:** V1 = *exact* duplicates only (identical `(platform, external_id)`, or identical normalized-text fingerprint → "possible duplicate" surfaced, not blocked when platforms differ). Near-duplicate detection is P12.
5. **Source deletion:** block with 409 when any `project_sources` row exists (recommended); otherwise delete rows and best-effort delete the raw file.

---

## 5. Backend

### 5.1 Module layout (NEW unless marked)

```
apps/api/app/ingestion/
  base.py            MODIFY  add fetch_transcript() to SourceExtractor
  youtube.py         MODIFY  captions via yt-dlp metadata, no media download
  registry.py        NEW     get_extractor(url) / extractors list (providers behind an interface)
  parsers.py         NEW     parse_srt / parse_vtt / parse_txt / parse_json3 → list[TranscriptSegment]
  normalize.py       NEW     normalize_segments(), fingerprint_text(), NORMALIZER_VERSION
  chunking.py        MODIFY  tolerate None timestamps
  service.py         NEW     add_source_from_url / add_source_from_transcript / ingest_transcript / retry_source / reconcile_stale
apps/api/app/workflows/
  runs.py            NEW     RunService (workflow_runs access); runner.py MODIFY only to accept a RunService callback
apps/api/app/api/v1/
  sources.py         NEW     source routes (replaces crud_router row for /sources)
  runs.py            NEW     GET /runs/{id}, GET /runs
  project_sources.py NEW     /projects/{id}/sources
  router.py          MODIFY  register new routers BEFORE crud routers; drop sources row; make transcripts read-only
apps/api/app/schemas/
  source.py          MODIFY  optional segment times; SourceAdd* request models
  resources.py       MODIFY  SourceVideoRead gains fields; SourceVideoUpdate loses `status`
apps/api/app/core/
  config.py          MODIFY  max_transcript_bytes, caption_languages
  errors.py          MODIFY  + SourceUnavailableError, NoCaptionsError, TranscriptParseError (all StoryWeaverError)
```

Likely, not mandatory: if the repository's conventions at implementation time favor a different split, follow them — but keep **routes thin and logic in `service.py`** ([adding a domain](../docs/development/adding-a-domain.md)).

### 5.2 Source identity, fingerprint and dedupe (deterministic)

| Origin | `platform` | `external_id` | `kind` | `url` |
| --- | --- | --- | --- | --- |
| YouTube video | `youtube` | 11-char video id from `classify_youtube_url` | `youtube` | canonical `https://www.youtube.com/watch?v=<id>` |
| Transcript upload/paste | `upload` | `sha256` of the **fingerprint text** (below) | `transcript` | `NULL` (optional user-supplied reference URL goes in `metadata`, never fetched) |

- **Fingerprint text** = lowercase, Unicode-NFKC, alphanumeric tokens joined by single spaces, computed from the *normalized* transcript. `source_videos.fingerprint` = `sha256(fingerprint text)` (hex). Pure function in `normalize.py`; unit-tested for formatting-insensitivity (SRT vs TXT of the same words → same fingerprint).
- For YouTube sources `fingerprint` is filled when the transcript becomes ready; a **later** upload whose fingerprint equals an existing source's returns that source with `already_exists=true, match="fingerprint"` instead of creating a second row.
- Idempotent creation relies on the existing `unique(platform, external_id)`; the service catches the unique violation and returns the existing row (no 409 for "add again").
- **Channel/video concepts now:** when the extractor returns `channel_external_id`/`channel_title` (yt-dlp `channel_id`, `channel`), the service **upserts a `Channel` row keyed by the canonical id (`UC…`), never the URL handle** (fixes KI-24) and sets `source_videos.channel_id`. `channels.url` = `https://www.youtube.com/channel/<id>`. No scan, no video listing, no sync — `YouTubeExtractor.list_videos` stays untouched until [P11](08-hardening-and-post-mvp.md).

### 5.3 Provider abstraction (YouTube stays behind it)

- `SourceExtractor` gains `fetch_transcript(self, url: str, languages: list[str]) -> ExtractedTranscript | None` (`ExtractedTranscript`: `segments`, `language`, `origin` ∈ {`manual`,`auto`}, `raw: bytes`, `raw_ext`). `extract()` stays metadata-only; the **service** composes them.
- `registry.get_extractor(url)` iterates registered extractors and returns the first whose `supports(url)` is true (today: YouTube only). The service never imports `youtube.py` directly; domain tables never store YouTube-specific fields outside `metadata`.
- **YouTube captions without downloading media (resolves KI-15):** yt-dlp already returns `subtitles` (human) and `automatic_captions` in the info dict when extracting with `skip_download`. `fetch_transcript` picks, in order: manual captions in `languages`, then automatic captions in `languages`; prefers format `json3`, then `vtt`; downloads **only the small caption file** with `httpx` (timeout, size cap `max_transcript_bytes`) from the URL yt-dlp returned. **SSRF guard:** require `https` and a hostname ending in `youtube.com`/`googlevideo.com`; refuse redirects to other hosts. Verify this host assumption against a real info dict during P1-T3 before coding the allow-list; if captions are served from other hosts, widen deliberately and document it.
- If yt-dlp is not installed: raise `ProviderNotConfiguredError("…uv sync --extra ingestion")` → 503 with that hint (needs KI-8 mapping).
- `faster-whisper` adapter: **untouched**. It would be wired only in a later phase together with an explicit, user-opt-in decision to fetch audio (that conflicts with "no media download for the library"); until then "no captions" means *upload a transcript*.

### 5.4 Normalization (deterministic, versioned)

`normalize_segments(segments) -> list[TranscriptSegment]`, `NORMALIZER_VERSION = "1"`:

1. NFC-normalize; strip control characters (keep `\n`); strip HTML-like caption tags (`<c>`, `<00:00:01.000>`), keep `[Music]`-style annotations as text (decision: keep, they are source content; revisit in P3).
2. Collapse whitespace; drop empty segments.
3. **De-duplicate YouTube auto-caption rolling repeats** (consecutive segments where the next starts with the previous text): keep the longer, merge times.
4. Merge segments shorter than 1.0 s into the previous one; enforce `end ≥ start`, monotonic starts (sort stable).
5. Output deterministic for identical input — covered by golden-file tests.

Cleaned `text` = segments joined with single spaces (paragraph breaks only for untimed TXT). Raw bytes are kept exactly as received (never mutated) so re-normalization with a newer `NORMALIZER_VERSION` is possible (creates a new transcript version).

### 5.5 Chunking

Reuse `chunk_segments(segments, max_chars=1200)` unchanged in behavior (chunk text/start/end). **MODIFY** only to accept `None` times (chunk start = first non-None, end = last non-None, else `None`). Chunks are written by **replace-by-transcript in one transaction** (delete existing chunks for that transcript id, insert new, `chunk_index` 0..n). `token_count` stays `NULL` (no tokenizer yet); `embedding` stays `NULL`.

### 5.6 Services and state machine

`source.add` (kind `source.add`, runs on `LocalRunner`):

```
create SourceVideo (status=discovered→importing) ──► extract() metadata ──► upsert Channel, fill metadata, status=imported
        └─► fetch_transcript() ──► ok: ingest_transcript() ──► Transcript ready + chunks + fingerprint
                                └► none: Transcript(status=failed, error=no_captions); source stays imported
```

`ingest_transcript(db, source, segments, origin, language, raw_bytes, raw_ext)` (also used by upload):

1. Normalize; compute fingerprint; if the source already has a current transcript with the **same fingerprint and same `normalizer_version`** → return it (idempotent no-op).
2. Store raw via `LocalStorage` at `transcripts/<source_id>/v<version>/raw.<ext>` (sanitized names, size cap enforced, `sha256` recorded).
3. In one DB transaction: set previous `is_current=false`, insert `Transcript(version=n+1, is_current=true, status=ready, …)`, replace chunks, update `source_videos.fingerprint`.
4. On any exception: transaction rolled back, raw file removed best-effort, `Transcript(status=failed, error=…)` recorded (separate transaction) so the failure is visible and retryable.

Status mapping (never invented by callers): `SourceStatus`: `discovered → importing → imported | failed`; `TranscriptStatus`: `pending → processing → ready | failed`. `failed` on the *source* = metadata could not be obtained; transcript trouble does **not** fail the source (it stays `imported` with a failed transcript).

### 5.7 Source usage tracking

`project_sources` already links projects and sources (composite PK, `role`). V1 adds:

- Endpoints to create/delete the link and list a project's sources / a source's projects (API below). `PUT` is idempotent.
- `usage_count` and a "used by" list in source responses (derived by join; no counter column).
- Search filter `exclude_used=true` ("avoid previously used sources") = sources with **no** `project_sources` row.
- **Not in V1:** idea-level reuse ("avoid previously used *ideas*") — needs P3/P4 artifacts (KI-22); fine-grained usage (which chunks/scenes used) is deferred. Source usage is therefore *project-level only* in V1; say so in the UI help text.

---

## 6. Database

One Alembic revision (**NEW**, autogenerate then hand-edit; follow [migrations](../docs/development/migrations.md); keep `CREATE EXTENSION` pattern untouched). `upgrade → downgrade → upgrade` and `alembic check` must pass in a test.

| Table | Change | Notes |
| --- | --- | --- |
| `source_videos` | `url` → **nullable**; ADD `kind VARCHAR(16) NOT NULL` (`youtube`/`transcript`, backfill `youtube`), `fingerprint VARCHAR(64) NULL` (index), `thumbnail_url VARCHAR(2048) NULL` | Fixes KI-14, KI-23 (thumbnail). Keep `unique(platform, external_id)`. Model defaults stay Python-side per repo convention |
| `transcripts` | ADD `raw_storage_key VARCHAR(1024) NULL`, `raw_sha256 VARCHAR(64) NULL`, `normalizer_version VARCHAR(16) NULL`, `is_current BOOLEAN NOT NULL` (default true in Python; backfill true); **partial unique index** `uq_transcripts_current` on `(source_video_id) WHERE is_current` | One current transcript per source; keeps `unique(source_video_id, version)` |
| `transcript_chunks` | ADD generated column `search_vector tsvector GENERATED ALWAYS AS (to_tsvector('simple', text)) STORED`; **GIN** index `ix_transcript_chunks_search_vector` | Declare with `sa.Computed(..., persisted=True)` in the model so `alembic check` stays clean. Embedding column/index untouched |
| `workflow_runs` | **NEW** (D1): `id`, `kind`, `subject_type`, `subject_id`, `status` (`queued/running/succeeded/failed/interrupted`, VARCHAR(32)), `attempt`, `idempotency_key` (unique), `params` JSONB, `progress` JSONB, `error` JSONB (`{code,message,retryable}`), `started_at`, `finished_at`, timestamps; indexes on `(subject_type, subject_id)`, `status` | Shared by every later phase; add enum `RunStatus` in `models/enums.py` |
| `project_sources` | none | Already sufficient for project-level usage |

Idempotency key for runs: `f"{kind}:{subject_id}:{attempt}"`; an **active** run (`queued`/`running`) for the same `(kind, subject_id)` is returned instead of starting a second one.
Retention: raw transcript files and rows are kept until the source is deleted; no automatic expiry in V1.
**Row for the canonical [idempotency-key table](../docs/workflows/retry-and-recovery.md#idempotency-keys)** (update that doc at phase end): `source.add` → `(platform, external_id)`; upload → `(platform='upload', sha256(fingerprint text))`; transcript version → `(source_video_id, fingerprint, normalizer_version)`.

## 7. API

All under `/api/v1`; no authentication (localhost only, [D14](IMPLEMENTATION_PLAN.md#7-technical-decisions-recommended-defaults)). Errors use FastAPI's `detail`; domain errors map via the KI-8 handler.

| Endpoint | Purpose | Request → response (concept) | Validation / errors | Idempotency |
| --- | --- | --- | --- | --- |
| `POST /sources/from-url` | Start adding a YouTube video | `{url}` → `202 {source, run}` (or `200 {source, run:null, already_exists:true}`) | `classify_youtube_url`; channel/playlist URL → `422 unsupported_kind` (message: channel import is a later release); other host/scheme → `422 invalid_url`; yt-dlp missing → `503` with install hint | By `(youtube, video_id)`: existing source returned, no second run unless `retry` |
| `POST /sources/from-transcript` | Add a transcript source | multipart: `file` (`.txt/.srt/.vtt`) **or** `text`; `title` (required), `language?`, `reference_url?` → `201 {source, transcript}` / `200 … already_exists:true,match:"fingerprint"` | ext allow-list; `max_transcript_bytes` (default 5 MB) → `413`; must decode as UTF-8 (BOM ok) else `422`; parse errors → `422 transcript_parse_error` with line number; filename sanitized, never used as a path; reference URL stored as text only | By fingerprint of normalized text |
| `GET /sources` | List with status | query `status?`, `kind?`, `used?`, `limit`, `offset` → items with `transcript_status`, `chunk_count`, `searchable`, `usage_count`, `thumbnail_url` | limits as other lists (1–200) | read |
| `GET /sources/{id}` | Detail | source + current transcript summary + channel | `404` | read |
| `PATCH /sources/{id}` | Edit title/description | `SourceVideoUpdate` (no `status`) | length limits; `null` on NOT NULL rejected `422` (not 409) | idempotent |
| `DELETE /sources/{id}` | Remove | → `204` | `409` if used by any project | idempotent |
| `GET /sources/{id}/transcript` | Current transcript | metadata + `text` + paged `segments` (`limit`, `offset`) | `404` if none | read |
| `GET /sources/{id}/chunks` | Chunks | paged | | read |
| `GET /sources/search` | Keyword search | `q` (1–200 chars), `exclude_used?`, `limit`, `offset` → hits `{source, chunk_id, snippet (highlighted), start_seconds, end_seconds, rank}` | `websearch_to_tsquery('simple', q)` (never raises on odd syntax); parameterized | read |
| `POST /sources/{id}/retry` | Retry failed metadata/transcript | → `202 {run}` | `409` if nothing to retry; returns the active run if one exists | single active run |
| `GET /sources/{id}/usage` | Projects using it | list | | read |
| `PUT /projects/{pid}/sources/{sid}` / `DELETE` / `GET /projects/{pid}/sources` | Link a source to a project | `{role?}` | `404` unknown ids; source must be searchable-or-imported | `PUT` idempotent |
| `GET /runs/{id}` · `GET /runs?subject_id=` | Poll job status | run with `status`, `error`, `attempt` | `404` | read |

Routing note (a real pitfall): `GET /sources/search` **must be registered before** `/sources/{id}` or `search` is parsed as a UUID and returns `422`. The new `sources.py` router is included before any generic route in `router.py`; add a test for it.
Removed in P1: `POST /sources`, `POST /transcripts`, `PATCH /transcripts/{id}`; `GET`/`DELETE` of transcripts remain read-only/guarded. Update `docs/api/resources/*` accordingly.

## 8. Frontend

Existing: `/sources` (index cards), `/sources/videos` (read-only list via `ResourceList`), `/sources/channels` (read-only, unchanged). Conventions: TanStack Query keyed by API path, `lib/api.ts` fetch wrapper, shadcn components, `StatusBadge`, `states.tsx` (empty/error/loading). **Zustand** is used only if shared UI state appears (e.g. selected source across panes); otherwise local state — do not add a store for its own sake.

| Task | File | Change |
| --- | --- | --- |
| UI-1 | `apps/web/src/lib/api.ts` | **MODIFY:** do not force `Content-Type: application/json` when the body is `FormData`; surface the API `detail` string in `ApiError.message` (currently ignored); typed helpers for new endpoints |
| UI-2 | `components/ui/{dialog,tabs,input,textarea,label}.tsx` | **NEW** via `pnpm dlx shadcn@latest add …` (needs network once) |
| UI-3 | `components/sources/add-source-dialog.tsx` | **NEW:** tabs **YouTube URL** / **Upload or paste**; client-side checks (non-empty, extension, size) mirroring server limits; submits mutation; shows duplicate notice ("already in your library") with a link; on `202` starts polling the run |
| UI-4 | `components/sources/use-run.ts` | **NEW:** `useQuery(['/runs', id])` with `refetchInterval` until terminal; invalidates `['/sources']` on completion |
| UI-5 | `app/sources/videos/page.tsx` | **MODIFY:** replace `ResourceList` with a richer list (title, kind icon, source status + transcript status badges, duration, "used in N projects", **Retry** on failure), the Add button, and a search box (`?q=`) that renders hits with snippet + timestamp |
| UI-6 | `app/sources/videos/[id]/page.tsx` | **NEW:** metadata card (thumbnail if present, channel, duration, language), failure panel with error code + Retry + "Upload transcript instead", transcript viewer (paged, timestamps when present), in-source search, usage list, "Add to project" picker |
| UI-7 | `app/projects/[id]/page.tsx` | **MODIFY (small):** list linked sources, add/remove link (full Studio stage UI is P9) |
| UI-8 | `app/sources/page.tsx` | **MODIFY:** index links to Videos with the add action; keep "Channels" card labelled *import arrives later* |

States required: empty library (with explanation of both add paths), loading skeletons, per-row failure with retry, API-unreachable error (existing), upload-too-large and parse-error messages from `detail`. Accessibility: dialog focus management (shadcn default), labelled inputs.

## 8a. Services / Workflows

Two persisted run kinds on the existing `LocalRunner` (no Temporal): **`source.add`** (create row → metadata → channel upsert → transcript fetch → normalize → chunk → persist) and **`source.fetch_transcript`** (the transcript half, used by retry after "no captions"/transient failure). Trigger: `POST /sources/from-url` or `/sources/{id}/retry`; inputs: the validated URL / source id; outputs: `SourceVideo` + current `Transcript` + chunks; persisted state: `source_videos.status`, `transcripts.status`, `workflow_runs`; retry: manual via `/retry` (automatic retry/backoff is P2); idempotency and failure behavior as in §13; downstream invalidation: none yet (a new transcript version later marks P3 analyses stale via `input_hash` — see [versioning](versioning-and-invalidation.md)); approval gates: none. Uploads are processed synchronously in the request (bounded by `max_transcript_bytes`) and call the same `ingest_transcript`. Step detail: §5.3, §5.6.

## 9. AI

**None in P1.** There is no model call, no embedding, no prompt. Responsibility split for this phase:

- *AI:* none. (Language is taken from caption metadata or user input — no model detection.)
- *Deterministic:* URL validation, extraction orchestration, parsing, normalization, fingerprinting, dedupe, chunking, persistence, FTS, usage, run state, retries, file storage.

Topic classification, summarisation and embeddings are **not** done here (P3 / P11).

## 10. Storage / media

- Raw transcript files only, under `STORAGE_ROOT/transcripts/<source_id>/v<n>/raw.<ext>` via `LocalStorage` (path-traversal-safe, streaming, size-capped, sha256) — first real use of the class. **Depends on KI-1 being fixed.**
- **No video/audio is downloaded or stored.** `skip_download` stays on; the caption fetch retrieves a text file only. Thumbnails are stored as a remote URL string (`thumbnail_url`), never fetched server-side.
- Nothing in `data/` is committed (git-ignored); tests use `tmp_path`/a temp `STORAGE_ROOT`.

## 11. Testing

Uses the existing stack ([testing strategy](../docs/testing/testing-strategy.md)). **No test performs network I/O; no claim is made that live YouTube extraction is tested** — it gets one documented manual check (P1-T16).

| Layer | Tests (files NEW in `apps/api/tests/` unless noted) |
| --- | --- |
| Unit | `test_parsers.py` (SRT/VTT/TXT/json3 golden files in `tests/fixtures/`, malformed input → `TranscriptParseError` with line), `test_normalize.py` (rolling-caption dedupe, tag stripping, idempotent output, `NORMALIZER_VERSION`), `test_fingerprint.py` (format-insensitive, sensitive to content), `test_chunking.py` (None timestamps), `test_youtube_captions.py` (recorded `info` JSON → language/format selection, manual-over-auto, no captions → `None`, host allow-list refusal, yt-dlp missing → `ProviderNotConfiguredError`) |
| DB | `test_models.py` additions: `uq_transcripts_current` partial unique, `search_vector` generated + GIN usable (`@@` query), nullable `url` + kind/unique, run table constraints; migration up/down/up + `alembic check` |
| Service | `test_ingestion_service.py` with a **fake extractor** (registry override): add-by-URL happy path; second add → no duplicate; no-captions path leaves source `imported` + transcript `failed`; failure mid-ingest rolls back chunks and removes raw file; same transcript twice → single version; changed text → version 2 with `is_current` swap; channel upsert by canonical id |
| API | `test_sources_api.py`: every endpoint above incl. `422/413/409/503` cases, `/sources/search` route-order test, `exclude_used`, retry returns active run, delete blocked when used, project link idempotent; update/remove tests that used the deleted raw routes (`test_api.py`) |
| Runs | `test_runs.py`: run lifecycle, single active run per `(kind, subject)`, stale-`importing` reconciliation at startup |
| Frontend (Vitest) | add-dialog validation (extension/size/empty), duplicate notice, `use-run` stops polling at terminal state, list renders statuses + retry, `api.ts` FormData header + `detail` message |
| E2E (Playwright, `apps/web/e2e/sources.spec.ts` NEW) | with the API running against the test DB: upload a transcript fixture → appears once → keyword search finds it → re-upload shows "already in your library"; uses the **upload path only** (no network). URL path is covered at API level with the fake extractor. On this OS run with `PLAYWRIGHT_CHROMIUM_PATH` |
| Security | traversal filenames, oversize, non-UTF-8, `file://`/foreign-host URLs, caption URL pointing at a foreign host |

## 12. Observability

Log events (structlog JSON, existing conventions; **never log transcript text or raw captions**, only counts/ids): `source.add.started|finished|failed`, `transcript.ingested`, `search.executed` (query length, hit count, duration — not the query text if it could be sensitive; decision: log length only). Fields: `workflow_id` (= run id), `source_id`, `platform`, `duration`, `status`, `error_code`. Counters stored in the run row (`progress`: `{step, segments, chunks}`). Note KI-2: do not name log keys with `token`/`key` substrings (e.g. use `chunk_count`, not `chunk_tokens`).

## 13. Failure handling and idempotency

| Failure | Behavior | Retryable |
| --- | --- | --- |
| Invalid / unsupported URL | `422` immediately; nothing created | n/a |
| yt-dlp not installed | `503` + hint; source not created | after install |
| Video unavailable / private / region-blocked | source `failed`, `error` code `video_unavailable` | no (user action) |
| Network/timeout/extractor error | run `failed`, `error.retryable=true`; source `failed` or transcript `failed` | yes (`/retry`) |
| No captions | transcript `failed` (`no_captions`); source `imported` | via upload |
| Caption file too large / unparsable | transcript `failed` with code; raw file removed | after fix |
| App stopped mid-run | startup `reconcile_stale()` (thin version in P1-T8; generalized in P2): runs `running` → `interrupted`, sources `importing` with no active run → `failed(interrupted)` | yes |
| Duplicate request / double click | existing source/run returned | — |
| Concurrent identical adds | unique constraint race handled by catching the violation and re-reading | — |

Every step is safe to re-run: re-running `ingest_transcript` with identical input is a no-op; chunk replacement is transactional.

---

## 14. Tasks

Each task: files, steps, tests, acceptance. Complete in order unless noted; `‖` = may run in parallel.

**P1-T1 — Verify prerequisites** · MODIFY nothing yet · Confirm P0 closed KI-1, KI-8 (or implement KI-8 handler here **only if P0 deferred it**, referencing [`01-foundation.md`](01-foundation.md)), KI-11/KI-19. *Accept:* a test shows `STORAGE_ROOT=` (empty) no longer resolves to `.`; a route raising `ProviderNotConfiguredError` returns 503.

**P1-T2 — Schemas and parsers** · `schemas/source.py` MODIFY (optional `start/end`; `SourceAddUrl`, `ExtractedTranscript`), `ingestion/parsers.py` NEW, `ingestion/chunking.py` MODIFY, fixtures NEW · Steps: implement SRT, VTT (incl. cue settings/tags), json3, TXT (paragraph split; untimed) parsers; enforce `max_transcript_bytes`; errors carry line numbers. *Accept:* parser + chunking unit tests green; untimed text yields chunks with `None` times.

**P1-T3 — Extractor captions (KI-15)** ‖ · `ingestion/base.py`, `youtube.py`, `registry.py` MODIFY/NEW · Steps: add `fetch_transcript`; language/format selection; guarded `httpx` fetch; recorded info/caption fixtures captured **once manually** and committed (strip personal data); verify host allow-list against a real info dict. *Accept:* `test_youtube_captions.py` green offline.

**P1-T4 — Normalizer and fingerprint** ‖ · `ingestion/normalize.py` NEW; `schemas/resources.py` MODIFY (`SourceVideoUpdate` without `status`, with limits) · *Accept:* normalizer golden tests + fingerprint tests green.

**P1-T5 — Migration and models** · `models/domain.py`, `models/enums.py` (RunStatus) MODIFY; Alembic revision NEW · Steps: columns/indexes/`workflow_runs` per §6; hand-edit generated column; model `Computed` so `alembic check` is clean. *Accept:* up/down/up and `alembic check` pass; DB constraint tests green.

**P1-T6 — Ingestion service** · `ingestion/service.py` NEW · Steps: `ingest_transcript` (§5.6), `add_source_from_transcript`, channel upsert, fingerprint dedupe, raw storage via `LocalStorage`, transactional chunk replace. *Accept:* service tests (upload path, versioning, rollback, idempotency) green.

**P1-T7 — Run service and URL flow** · `workflows/runs.py` NEW, `runner.py` MODIFY (callback), `service.add_source_from_url` · Steps: create run, execute on `LocalRunner`, update `progress`, persist failure with `{code,message,retryable}`. *Accept:* fake-extractor URL flow test: source reaches `imported`, transcript `ready`, run `succeeded`; failure flows persist errors.

**P1-T8 — Reconciliation** · `service.reconcile_stale`, `main.py` MODIFY (startup hook) · *Accept:* test seeds a `running` run + `importing` source → after startup both marked interrupted/failed.

**P1-T9 — Source and run routes** · `api/v1/sources.py`, `runs.py`, `router.py` MODIFY; `pyproject.toml` MODIFY (`python-multipart`) · Steps: all `/sources` routes in §7 (search registered first); remove raw create/patch of sources/transcripts; update affected existing tests. *Accept:* `test_sources_api.py` green, including route-order and error cases; OpenAPI lists the new routes.

**P1-T10 — Search and usage** · `service`/routes · Steps: `websearch_to_tsquery('simple')` with `ts_headline` snippets and `ts_rank`; `exclude_used`; usage endpoints and project link routes. *Accept:* ranking/snippet/exclude tests green; query with punctuation/quotes never errors.

**P1-T11 — Thumbnail and metadata mapping** · service · Steps: map `thumbnail_url`, `duration`, `published_at`, `language`, channel; store unmapped extras in `metadata`. *Accept:* mapping test from recorded info JSON.

**P1-T12 — Frontend foundation (UI-1, UI-2)** · *Accept:* Vitest for `api.ts` (FormData, `detail`); shadcn components present; `make lint` clean.

**P1-T13 — Add-source flow (UI-3, UI-4)** · *Accept:* Vitest for dialog + polling hook green.

**P1-T14 — List, detail, search, usage UI (UI-5…UI-8)** · *Accept:* Vitest for list/detail states; manual check of empty, loading, failed (retry), duplicate, no-captions → upload fallback.

**P1-T15 — E2E** · `apps/web/e2e/sources.spec.ts` NEW · *Accept:* Playwright spec green against the test-DB API (upload → search → duplicate notice).

**P1-T16 — Live check and docs** · One **manual**, recorded run of a real YouTube URL on the dev machine (needs `--extra ingestion` and network); record result and date in `docs/` status notes (success or failure — do not claim more). Update docs listed in §16. *Accept:* checklist in §15 satisfied; status.md reflects reality.

## 15. Acceptance criteria (Checkpoint B)

1. `make lint` clean; `make test` green **with `TEST_DATABASE_URL` set** (DB tests ran, none skipped for this phase); `make e2e` green for the new spec; migration up/down/up and `alembic check` clean.
2. Adding the same YouTube URL twice (fake extractor) yields **one** `source_videos` row and one transcript version; the second call returns `already_exists=true`.
3. Uploading a transcript as TXT, SRT and VTT with the same words yields **one** source (same fingerprint); changing the text creates transcript version 2 and flips `is_current`.
4. After ingest, `GET /sources/search?q=<word from transcript>` returns the source with a highlighted snippet; the source is `searchable=true`; a source whose transcript failed is `searchable=false` and still listed.
5. A video with no captions ends with source `imported`, transcript `failed (no_captions)`, and the UI offers "Upload transcript instead".
6. Failure injection (extractor raises mid-run) leaves **no** orphan chunks/raw file, records `error.code`, and `POST /sources/{id}/retry` completes it on the next attempt.
7. Killing the API mid-run and restarting leaves no source stuck in `importing` and no run stuck `running`.
8. `PUT /projects/{id}/sources/{sid}` is idempotent; `GET /sources/{id}/usage` lists the project; `exclude_used=true` omits it; deleting a used source returns 409.
9. No media file exists under `STORAGE_ROOT` after any flow; `skip_download` remains set; the only network fetch in the extractor is the caption file from an allow-listed host (unit-tested refusal otherwise).
10. Security tests pass: traversal filenames, oversize (413), non-UTF-8 (422), foreign-host/`file://` URLs rejected.
11. UI: all states in §8 reachable and covered by tests; no console errors in the e2e run.
12. Documented live YouTube check performed once and honestly recorded (pass/fail) — **or** explicitly recorded as not performed.

## 16. Deliverables

Working Source Library V1 (UI + API + persistence + search + usage + retry), one migration, `workflow_runs` table and `RunService`, parsers/normalizer/fingerprint, caption-capable YouTube extractor behind a registry, fixtures and tests, and **docs updated**: [`status.md`](../docs/reference/status.md) (rows for source extraction, transcripts, usage, thumbnail; close KI-12/13/14/15/23/24; note KI-9 partially closed — `LocalStorage` now used by routes), [source library](../docs/domains/source-library.md), [channel ingestion](../docs/domains/channel-ingestion.md) (linkage only), [transcript pipeline](../docs/domains/transcript-pipeline.md), [ingestion](../docs/workflows/ingestion-workflow.md) and [transcript](../docs/workflows/transcript-workflow.md) workflows, [idempotency table](../docs/workflows/retry-and-recovery.md#idempotency-keys), [`api/resources/source-videos.md`](../docs/api/resources/source-videos.md) / [`transcripts.md`](../docs/api/resources/transcripts.md), [data models](../docs/data/source-data-model.md), [database schema](../docs/data/database-schema.md), [frontend routing](../docs/frontend/routing.md), [testing strategy](../docs/testing/testing-strategy.md) (counts), changelog.

## 17. Dependencies

- **Depends on:** P0 ([`01-foundation.md`](01-foundation.md)).
- **Depended on by:** P2 (reuses `workflow_runs`/`RunService` and generalizes them — [`03-…`](03-intelligence-runtime-and-understanding.md)), P3 (reads the current transcript's chunks), P9 (source stage UI), P11 (channel import/sync, embeddings, semantic search — [`08-…`](08-hardening-and-post-mvp.md)).
- **Contracts handed forward:** `source_videos.id` + current transcript (`is_current`) are the sole inputs P3 may use; `fingerprint` + `normalizer_version` feed `input_hash` for source-derived artifacts ([versioning design](versioning-and-invalidation.md)).

## 18. Do NOT

- Do not download video/audio or call `faster-whisper` in this phase; do not add a media-download option "for later".
- Do not implement channel scan/import/sync, embeddings, topic classification, or any LLM call.
- Do not leave a raw `POST /sources`/`/transcripts` path that bypasses validation.
- Do not store YouTube-specific logic outside `ingestion/youtube.py` (fields beyond the normalized set go to `metadata`).
- Do not change the existing `unique(platform, external_id)`, `unique(source_video_id, version)`, or the embedding column/index.
- Do not log transcript text or captions; do not fetch arbitrary URLs; do not use user filenames as paths.
- Do not mark live YouTube extraction "tested" without the recorded manual run.
- Do not commit or push unless the user asks.
