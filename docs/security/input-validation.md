# Input Validation

> What is validated, where, and what is missing.

## Status

Partially implemented.

## API layer

Pydantic models in `schemas/resources.py`: string length limits (`title` ≤ 512, `url` ≤ 2048, etc.), `ge`/`le` bounds on `limit` (1–200) and `offset` (≥ 0), `sequence ≥ 1`, topic slug regex `^[a-z0-9]+(?:-[a-z0-9]+)*$`, enum membership for statuses/types, UUID path parameters, `extra="forbid"` on PATCH bodies. Invalid input → `422`. Integrity violations (duplicates, bad foreign keys) → `409`.

**Update models are weaker than create models** ([KI-4](../reference/status.md#known-issues-and-limitations)): the `*Update` schemas carry **no length limits**, so a PATCH with an over-long string passes validation, reaches PostgreSQL and fails there with `500` (a database data error is not mapped). They also accept an explicit `null`: on a nullable column this clears the value, and on a NOT NULL column it raises an integrity error that the factory reports as a misleading `409 conflict or invalid reference`. New update schemas should add `max_length` and reject `null` for required fields. Typed `StoryWeaverError`s raised in routes would also surface as `500` ([KI-8](../reference/status.md#known-issues-and-limitations)).

Gaps: `platform` is a free string; `settings`/`segments` JSON blobs are unvalidated dicts; create models do not forbid extra fields; `channels.url` and `source_videos.url` are only length-checked at the API (the YouTube allow-list is not applied on create) — **a client can store any URL string** ([KI-12](../reference/status.md#known-issues-and-limitations)). `classify_youtube_url` runs only inside `YouTubeExtractor`; API-created rows are not URL-validated, so any future code that fetches a stored `url` must re-validate it.

## Source URLs

`classify_youtube_url`: scheme http/https; hostname exactly in `{youtube.com, www., m., music.youtube.com, youtu.be}` (parsed hostname, so `youtube.com.evil.com` fails); 11-char video ids; playlist and channel patterns; length ≤ 2048. `YouTubeExtractor` calls this before yt-dlp. Metadata extraction uses `skip_download` and flat listing — the library design does not require downloading video files ([ingestion workflow](../workflows/ingestion-workflow.md)). A Whisper fallback would need audio; that is Planned and must be an explicit, user-authorised step.

## Model output

Validated via Pydantic schemas ([structured output](../ai/structured-output.md)); `SceneSpec` fields are typed and `camera` values are literals.

## Files

[File security](file-security.md). Other source types (TXT/SRT/VTT parsers) do not exist yet; when added, cap size, bound parse effort, and treat content as untrusted text.
