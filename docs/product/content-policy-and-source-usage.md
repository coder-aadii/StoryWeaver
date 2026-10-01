# Content Policy and Source Usage

> Rules for how StoryWeaver should use third-party source material, and what the code enforces today.

## Status

**Partially implemented.** URL validation and server-side secrets are implemented; originality enforcement, attribution tracking and policy checks are **Planned — not implemented**. This is product guidance, **not legal advice**.

## Principles

1. **Authorised use only.** Ingestion tools (e.g. `yt-dlp`) must be used only for content the user is authorised to use, respecting platform terms and applicable law. The README states this; the code does not and cannot verify authorisation.
2. **Original output.** The product goal is stories that use sources for facts, concepts and events and add their own structure, hook, pacing, framing and wording, rather than paraphrasing or reproducing the source ([story-generation](../domains/story-generation.md)). This is an engineering and product goal, measured by planned similarity checks; it is **not** a legal determination and no check guarantees any legal outcome.
3. **Transparency.** Each project should keep a record of which sources it drew on (`project_sources` table exists; recording and surfacing are Planned).
4. **Minimal retention.** Store what the pipeline needs (metadata, transcripts, chunks); do not download media unless a workflow requires it. Today no media download occurs.
5. **No misleading content.** Generated narration and visuals should not impersonate real people or fabricate quotes as fact. Enforcement approach is **Decision pending**.

## What the code enforces today

| Concern | Enforcement | Where |
| --- | --- | --- |
| Only YouTube hosts accepted for YouTube extraction; schemes limited to http(s); ids pattern-checked | Implemented in the extractor **and** at the creation routes: sources exist only via `POST /sources/from-url` (YouTube video URLs; the raw `POST /sources` was removed in P1) and `POST /sources/from-transcript`; `POST /channels` validates its URL (previously KI-12, resolved in P0/P1). Update endpoints cannot change `url`; any future fetch must still re-validate | `ingestion/youtube.py` → [input-validation](../security/input-validation.md) |
| No shell invocation of user input; yt-dlp used via Python API | Implemented | [file-security](../security/file-security.md) |
| Provider keys not exposed to the browser; logs mask secret-named keys and scrub secret-shaped values, including exception text (best-effort) | Partial | [secrets](../security/secrets.md) |
| Unique source per `(platform, external_id)` (no silent duplicates) | Implemented | [source-library](../domains/source-library.md) |

## Planned controls (Target)

- Similarity check between a script and its source chunks, and against previous projects and previously used ideas, using embeddings plus n-gram overlap, with a flag/rejection threshold (**Decision pending**). No storage for used ideas exists yet ([KI-22](../reference/status.md#known-issues-and-limitations)) — see [story-generation-pipeline](../ai/story-generation-pipeline.md) and the data direction in [embeddings-and-vector-search](../data/embeddings-and-vector-search.md).
- Source attribution list stored per project and rendered in output metadata.
- Provenance on generated assets (provider, model, prompt version) — fields exist on `script_versions`; asset provenance would live in `assets.metadata` (convention proposed, not implemented — **Planned**).
- A per-source "usage allowed" flag set by the user (**Decision pending**).
- Content-safety review step before render (**Decision pending**).

## Third-party licences

- **Remotion** requires a company licence above a size threshold; the Player logs a reminder until `acknowledgeRemotionLicense` is set, intentionally left to the owner ([README](../../README.md)).
- Model licences (image/LLM/TTS weights) differ; selection and recording of licences is part of [provider-selection](../ai/provider-selection.md).
- Music/SFX must come from sources whose licence permits use in published videos (**Planned**; see [music-and-sfx](../media/music-and-sfx.md)).

## Untrusted input

Transcripts and any fetched content are untrusted: they can contain text that tries to steer an LLM (prompt injection). Treat them as data, never as instructions — see [threat-model](../security/threat-model.md) and [prompting-strategy](../ai/prompting-strategy.md).

## Out of scope

Publishing/uploading videos, monetisation advice, takedown handling.

## Open questions

Retention period for raw transcripts; whether to store source URLs in rendered video descriptions automatically; handling of age-restricted or private content (not supported).
