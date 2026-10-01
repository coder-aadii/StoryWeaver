# Input Validation

> What is validated, where, and what is missing.

## Status

Partially implemented.

## API layer

Pydantic models in `schemas/resources.py`: string length limits (`title` ≤ 512, `url` ≤ 2048, etc.), `ge`/`le` bounds on `limit` (1–200) and `offset` (≥ 0), `sequence ≥ 1`, topic slug regex `^[a-z0-9]+(?:-[a-z0-9]+)*$`, enum membership for statuses/types, UUID path parameters, `extra="forbid"` on PATCH bodies. Invalid input → `422`. Integrity violations (duplicates, bad foreign keys) → `409`.

**Update models** are validated like create models (previously KI-4, resolved in P0): `*Update` schemas carry `min_length`/`max_length` limits, unknown fields are rejected (`extra="forbid"`), and an explicit `null` is rejected with 422 on NOT NULL fields (it clears only the declared nullable fields). A database `DataError` that slips through maps to `422 invalid_value`. New update schemas should declare `nullable_fields` and length limits. Typed `StoryWeaverError`s raised in routes are mapped to HTTP statuses with a stable `code` (previously KI-8, resolved in P0; see [API errors](../api/errors.md)).

Gaps: `platform` is a free string (≤32 characters); `settings`/`segments` JSON blobs are unvalidated dicts (`segments` is capped at 100,000 items); create models do not forbid extra fields. URLs: `POST /channels` and `POST /sources` validate `url` on create — for `platform=youtube` it must be a YouTube channel / video URL respectively (`classify_youtube_url`), for other platforms an `http(s)` URL; update schemas cannot change `url` (previously KI-12, resolved for create in P0). The extractor still validates independently, and any future code that fetches a stored `url` must re-validate it.

## Source URLs

`classify_youtube_url`: scheme http/https; hostname exactly in `{youtube.com, www., m., music.youtube.com, youtu.be}` (parsed hostname, so `youtube.com.evil.com` fails); 11-char video ids; playlist and channel patterns; length ≤ 2048. `YouTubeExtractor` calls this before yt-dlp. Metadata extraction uses `skip_download` and flat listing — the library design does not require downloading video files ([ingestion workflow](../workflows/ingestion-workflow.md)). A Whisper fallback would need audio; that is Planned and must be an explicit, user-authorised step.

## Model output

Validated via Pydantic schemas ([structured output](../ai/structured-output.md)); `SceneSpec` fields are typed and `camera` values are literals.

## Files

[File security](file-security.md). Other source types (TXT/SRT/VTT parsers) do not exist yet; when added, cap size, bound parse effort, and treat content as untrusted text.
