# Transcript Pipeline

> Turning a source's speech into clean, timestamped, chunked, embeddable text.

## Status

**Partially implemented** — `Transcript`/`TranscriptChunk` tables, `chunk_segments`, a transcription interface with a lazy faster-whisper adapter. Extraction from YouTube captions, cleaning, persistence and embedding are **Planned — not implemented**.

## Purpose

Produce the canonical text representation of a source that every later stage reads.

## Problem being solved

Raw captions are noisy (auto-caption errors, no punctuation, duplicated lines, timing overlaps). Analysis and retrieval quality depend on normalization, and provenance must be kept so a bad transcript can be re-derived.

## Inputs

Platform captions (manual or auto), uploaded TXT/SRT/VTT, or audio for local transcription.

## Outputs

| Representation | Where |
| --- | --- |
| Raw transcript (as received) | **Decision pending.** The `transcripts` table has one `text` column, `segments` JSONB and no storage-key column, so a raw copy has nowhere to be recorded today. Options: a file under `data/transcripts/` with a key kept in a new column, or keep only the normalised form. Raw-vs-cleaned is not modelled |
| Transcript text | `transcripts.text` (single column; whether it holds raw or cleaned text is not yet defined) |
| Timestamped segments | `transcripts.segments` JSONB `[{start, end, text, speaker?}]` (`TranscriptSegment`) |
| Chunks | `transcript_chunks` rows (`text`, `start_seconds`, `end_seconds`, `token_count`, `embedding`, `embedding_model`) |

## Entities

`Transcript` (`status`: pending → processing → ready/failed; `origin`: manual / auto / whisper / upload — free-form string today; `version`; `language`; `error`), `TranscriptChunk`.

## Workflow (Target Architecture)

1. Acquire: platform captions first (cheap); fall back to local speech-to-text (`Transcriber`, faster-whisper) if absent.
2. Keep the raw artefact untouched *(where it is stored is Decision pending, see Outputs)*.
3. Normalize: parse SRT/VTT, merge overlapping cues, fix whitespace/encoding, strip sound-tags, optionally restore punctuation.
4. Optional LLM clean-up (typo/punctuation) — never altering meaning; record that it happened (Decision pending).
5. Segment → chunk (`chunk_segments`, ~1200 chars, timing preserved).
6. Embed chunks ([embeddings](../ai/embeddings.md)), store vectors.
7. Mark `ready`.

See [transcript workflow](../workflows/transcript-workflow.md).

## Business rules

- **Target:** never overwrite a transcript; create a new `version`. **Current limitation ([KI-13](../reference/status.md#known-issues-and-limitations)):** the API cannot set `version` (DB default 1, unique `(source_video_id, version)`), so a second transcript for a video returns 409; `origin` defaults to `unknown` in the DB but `upload` in the API schema.
- Chunks keep `start_seconds`/`end_seconds` so any retrieved passage can cite its position in the source.
- `embedding_model` is recorded per chunk; mixing models in one search is invalid; the vector dimension (768) is fixed in the schema.
- Language must be recorded; wrong-language transcripts are a failure, not a silent pass.

## AI responsibilities

Optional transcript repair; later, embeddings. Local Whisper is a model but a deterministic-in-intent *extraction* step, not a creative one.

## Deterministic responsibilities

Parsing, normalization, chunk boundaries, timestamps, storage, versioning, status.

## Current implementation

- Metadata-only extractor ([KI-15](../reference/status.md#known-issues-and-limitations)): `YouTubeExtractor.extract()` does not fetch captions or audio; caption fetching, SRT/VTT parsing and audio acquisition are **new code**, not wiring.
- `FasterWhisperTranscriber` (optional `transcription` extra; model loaded on first use only; streams segments; **not tested against real audio**).
- `TranscriptionResult` returns `language` and `segments`; word-level timestamps and speaker info are *not* produced yet.
- `chunk_segments` — tested for grouping and timing preservation (character-based; not token-aware).
- `/api/v1/transcripts` create/list/get/patch/delete only.

## Planned implementation

Caption fetch, SRT/VTT/TXT parsers, cleaning, persistence, token-aware chunking, embedding job, word timestamps, diarisation.

## Edge cases

No speech/music-only video; mixed languages; extremely long audio (process by file, not in RAM); caption timing drift; duplicate overlapping auto-caption lines.

## Open questions

Chunk size/overlap tuning; token counting library; whether to keep an LLM-cleaned copy separate from the deterministic normalization; where the raw transcript lives (Decision pending); how an upload with no URL is represented ([KI-14](../reference/status.md#known-issues-and-limitations)).
