# Input Validation

> What is validated, where, and what is missing.

## Status

Partially implemented. The Source Library inputs (YouTube URLs, transcript uploads, search queries) are validated end to end since P1 (2026-10-01).

## API layer

Pydantic models in `schemas/resources.py`: string length limits (`title` ≤ 512, `url` ≤ 2048, etc.), `ge`/`le` bounds on `limit` (1–200) and `offset` (≥ 0), `sequence ≥ 1`, topic slug regex `^[a-z0-9]+(?:-[a-z0-9]+)*$`, enum membership for statuses/types, UUID path parameters, `extra="forbid"` on PATCH bodies. Invalid input → `422`. Integrity violations (duplicates, bad foreign keys) → `409`.

**Update models** are validated like create models (previously KI-4, resolved in P0): `*Update` schemas carry `min_length`/`max_length` limits, unknown fields are rejected (`extra="forbid"`), and an explicit `null` is rejected with 422 on NOT NULL fields (it clears only the declared nullable fields). A database `DataError` that slips through maps to `422 invalid_value`. New update schemas should declare `nullable_fields` and length limits. Typed `StoryWeaverError`s raised in routes are mapped to HTTP statuses with a stable `code` (previously KI-8, resolved in P0; see [API errors](../api/errors.md)).

Gaps: `platform` is a free string (≤32 characters); `settings`/`segments` JSON blobs are unvalidated dicts (`segments` is capped at 100,000 items); create models do not forbid extra fields. URLs: `POST /channels` validates `url` on create — for `platform=youtube` it must be a YouTube channel URL (`classify_youtube_url`), for other platforms an `http(s)` URL; sources are created only through `POST /sources/from-url` (YouTube video URLs only) and `POST /sources/from-transcript`, so there is no unvalidated path (the raw `POST /sources` was removed in P1, previously KI-12); update schemas cannot change `url` (previously KI-12, resolved for create in P0). The extractor still validates independently, and any future code that fetches a stored `url` must re-validate it.

## Source URLs

`classify_youtube_url`: scheme http/https; hostname exactly in `{youtube.com, www., m., music.youtube.com, youtu.be}` (parsed hostname, so `youtube.com.evil.com` fails); 11-char video ids; playlist and channel patterns; length ≤ 2048. `YouTubeExtractor` calls this before yt-dlp. Metadata extraction uses `skip_download` and flat listing — the library design does not require downloading video files ([ingestion workflow](../workflows/ingestion-workflow.md)). A Whisper fallback would need audio; that is Planned and must be an explicit, user-authorised step.

## Source Library inputs (P1)

- **`POST /sources/from-url`:** the URL is classified without network access (`identify`); channel/playlist → `422 unsupported_kind`; anything not a YouTube video URL → `422 invalid_source`; optional dependency missing → `409 provider_not_configured` before any row is created.
- **Transcript upload/paste:** exactly one of `file`/`text`; non-blank `title` (≤ 1024); `language` ≤ 16; `reference_url` `http(s)`; extension allow-list; size cap; strict UTF-8; bounded parsing with line-numbered errors ([file security](file-security.md)).
- **Search:** `q` 1–200 characters, `limit` 1–50; the query is passed as a bound parameter to `websearch_to_tsquery`, which never raises on odd syntax (tested with quotes, operators, SQL fragments); only the query *length* is logged.
- **Output encoding:** snippets are HTML-escaped on the server; the web app never uses `dangerouslySetInnerHTML` for them.

## Model output

Validated via Pydantic schemas ([structured output](../ai/structured-output.md)); `SceneSpec` fields are typed and `camera` values are literals.

## Files

[File security](file-security.md). TXT/SRT/VTT/json3 parsers exist and follow those rules (capped size, bounded parse effort, content treated as untrusted text). Other source types (local audio/video, web documents) do not exist yet and must follow the same rules.
