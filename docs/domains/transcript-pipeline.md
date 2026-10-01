# Transcript Pipeline

> Turning a source's speech into clean, timestamped, chunked, searchable text.

## Status

**Implemented for captions and uploads (P1, 2026-10-01):** acquisition (YouTube captions or an uploaded/pasted `.txt`/`.srt`/`.vtt`), parsing, deterministic normalization, raw-file storage, versioning, chunking and keyword search. **Not implemented (Planned):** speech-to-text from audio (the faster-whisper adapter exists but is **not wired**), LLM clean-up, embeddings, word-level timing, diarisation. See the [status matrix](../reference/status.md).

## Purpose

Produce the canonical text representation of a source that every later stage reads.

## Problem being solved

Raw captions are noisy (auto-caption errors, no punctuation, rolling duplicated lines, markup, timing overlaps). Analysis and retrieval quality depend on normalization, and provenance must be kept so a bad transcript can be re-derived.

## Inputs

Platform captions (manual or automatic — `json3` or `vtt`), or an uploaded/pasted `.txt` / `.srt` / `.vtt` (UTF-8, BOM tolerated, ≤ `MAX_TRANSCRIPT_BYTES` = 5 MB). Audio for local transcription is **not** an input today.

## Outputs

| Representation | Where |
| --- | --- |
| Raw transcript, exactly as received (never mutated) | `STORAGE_ROOT/transcripts/<source_id>/v<n>/raw.<ext>`; key in `transcripts.raw_storage_key`, hash in `raw_sha256` |
| Cleaned text | `transcripts.text` — normalized segments joined with single spaces (a blank line between untimed paragraphs) |
| Timestamped segments | `transcripts.segments` JSONB `[{start, end, text, speaker?}]`; `start`/`end` are `null` for plain text — times are never fabricated |
| Chunks | `transcript_chunks` rows (`text`, `start_seconds`, `end_seconds`; `token_count` and `embedding` stay NULL), plus a generated `search_vector` |
| Fingerprint | `source_videos.fingerprint` (sha256 of the normalized, token-reduced text) |

So **raw vs cleaned is now modelled**: the raw file is the original; the database holds the cleaned form. Re-normalizing with a newer `NORMALIZER_VERSION` creates a new transcript version rather than editing one.

## Entities

`Transcript` (`status`: pending → processing → ready/failed; `origin`: `manual` / `auto` (platform captions) / `upload` — `unknown` only on failed placeholder rows; `version`; `is_current`; `language`; `normalizer_version`; `error`), `TranscriptChunk`.

## Workflow

Implemented path (detail in the [transcript workflow](../workflows/transcript-workflow.md)):

1. **Acquire.** Platform captions through `SourceExtractor.fetch_transcript` (manual before automatic; exact language before prefix; `json3` before `vtt`; automatic captions are an HLS playlist whose WebVTT segments are fetched individually), or an upload through `parse_transcript`. Only a caption/text file is ever fetched.
2. **Parse** (`ingestion/parsers.py`): SRT, VTT (header, `NOTE`/`STYLE` blocks, cue settings, hours optional, comma or dot milliseconds), json3, plain text (paragraphs, split at ≤ ~1,000 characters at sentence boundaries). Malformed input raises `TranscriptParseError` with a line number; an empty or whitespace-only file is rejected.
3. **Normalize** (`ingestion/normalize.py`, `NORMALIZER_VERSION = "2"`): Unicode NFC; strip control characters; strip HTML-like caption markup and timing tags without leaving a space (`<br>`/`<p>` become whitespace); unescape common entities; keep annotations such as `[Music]` (they are source content); collapse whitespace; drop empty segments; collapse YouTube auto-caption rolling repeats; merge segments shorter than 1.0 s into the previous one; sort stably and enforce `end ≥ start`. Untimed segments pass through untouched. The result is idempotent.
4. **Fingerprint and decide:** same fingerprint + same `normalizer_version` as the current ready transcript → no-op.
5. **Store raw** via `LocalStorage` (path-traversal-safe, streaming, size-capped, sha256 recorded).
6. **Persist in one transaction:** previous transcript `is_current = false`; new `Transcript` (version + 1, `ready`); chunks (`chunk_segments`, ~1,200 characters, timing preserved, `None` tolerated); update `source_videos.fingerprint`/`language`. On any failure the transaction rolls back and the raw file is removed.
7. **Mark ready.** If a source has no usable transcript, a `failed` transcript row records the error (e.g. `no_captions`) so the UI can show it.

Planned (not implemented): optional LLM clean-up (never altering meaning, recorded as such — Decision pending), speech-to-text for videos without captions, embedding of chunks ([embeddings](../ai/embeddings.md)).

## Business rules

- **Never overwrite a transcript; create a new `version`.** Versions are created only by the ingestion service (the old raw `POST/PATCH /transcripts` routes were removed; resolved KI-13). Exactly one version per source is `is_current` (partial unique index `uq_transcripts_current`); history rows keep their chunks but only the current, ready transcript is searchable.
- A failed attempt never replaces a ready current transcript; when a newer version succeeds, the failed row remains as non-current history.
- Chunks keep `start_seconds`/`end_seconds` so any retrieved passage can cite its position in the source.
- `embedding_model` is recorded per chunk when embeddings exist; mixing models in one search is invalid; the vector dimension (768) is fixed in the schema.
- Language is recorded when known (caption metadata or user input). No model detects it.

## AI responsibilities

None in V1. Later: optional transcript repair, embeddings. Local Whisper would be a model but a deterministic-in-intent *extraction* step.

## Deterministic responsibilities

Parsing, normalization, fingerprinting, chunk boundaries, timestamps, storage, versioning, status.

## Current implementation

- `parsers.py` (`parse_srt/vtt/json3/txt`, `parse_transcript`), `normalize.py` (`normalize_segments`, `cleaned_text`, `fingerprint_text`, `fingerprint`), `chunking.py`, `service.ingest_transcript`; golden-file tests, including idempotence and Unicode.
- `POST /sources/{id}/transcript` attaches or replaces a transcript on an existing source (the fallback when a video has no captions); identical content is a no-op.
- `FasterWhisperTranscriber` (optional `transcription` extra; lazy model load) and `TranscriptionResult` exist but **nothing calls them**; word-level timestamps and speaker info are not produced.
- `chunk_segments` is character-based, not token-aware.
- `/api/v1/transcripts` is read-only (`GET` list/detail); content is read through `GET /sources/{id}/transcript` and `/chunks`.

## Current limitations

- **Stray spaces from inline tags (KI-27):** fixed in normalizer version 2. A transcript stored under version 1 keeps its old text (e.g. `volcanoes .`) until it is re-ingested, which creates a new version.
- Normalization is deterministic and conservative: auto-caption errors and missing punctuation are not repaired.
- Each `fetch_transcript` call repeats yt-dlp's metadata extraction.
- Automatic-caption-only videos were not exercised live (HLS resolution is covered by recorded fixtures); see the [verification record](../reference/status.md#verification-record).

## Planned implementation

Token-aware chunking, embedding job, speech-to-text fallback (explicit opt-in because it needs audio), word timestamps, diarisation.

## Edge cases

No speech/music-only video; mixed languages; extremely long transcripts (stored and chunked, never held as media); caption timing drift; duplicate overlapping auto-caption lines (handled by the rolling-repeat rule); `[Music]`-style annotations (kept); plain text without any timestamps (chunks have `null` times).

## Open questions

Chunk size/overlap tuning; token counting library; whether to keep an LLM-cleaned copy separate from the deterministic normalization; whether `[Music]`-style annotations should be dropped for analysis (revisit in P3).
