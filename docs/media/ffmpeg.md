# FFmpeg

> Role of FFmpeg in StoryWeaver's media stack.

## Status

**Partially implemented** — FFmpeg is used only indirectly: Remotion ships its own `ffmpeg`/`ffprobe` binaries and uses them to encode. **A system-wide FFmpeg is not required** to render today, and **StoryWeaver has no FFmpeg code of its own** (no wrapper module, filter graphs or subprocess calls). The role of FFmpeg beyond Remotion's bundled encoder is **Decision pending**.

## Current implementation

- Remotion invokes its **bundled** FFmpeg to stitch frames and audio into an H.264 MP4. The render needs no system FFmpeg.
- A system FFmpeg/ffprobe is useful only for manual inspection of the sample render (codec, size, fps, duration) and for the future StoryWeaver-owned FFmpeg code below. It was used by hand during development and is not part of the codebase.
- The root `README.md` currently lists system FFmpeg as a prerequisite; that wording is outdated and is tracked in [KI-26](../reference/status.md#known-issues-and-limitations). Environment notes: [setup](../development/setup.md).

## Target Architecture (Planned — not implemented)

If the pipeline needs capabilities Remotion's bundled encoder does not provide, the choice between using Remotion's bundled binaries and requiring a system FFmpeg is **Decision pending**. An `app/video` helper layer using `subprocess` with **argument lists only** (never shell strings, never user-provided flags), responsible for:

| Task | Why FFmpeg |
| --- | --- |
| Probing media (`ffprobe`) | Measure real audio duration for the timeline ([voice-pipeline](voice-pipeline.md)) |
| Audio post-processing | Loudness normalisation (`loudnorm`), limiting, format conversion, resampling ([music-and-sfx](music-and-sfx.md)) |
| Final encoding / muxing | Hardware- or preset-specific encodes if Remotion's default is insufficient |
| Thumbnail / frame extraction | Poster images, QA frame sampling ([quality-assurance](../domains/quality-assurance.md)) |
| Subtitle muxing/export | Soft-sub tracks, SRT/VTT conversion |
| Optional full-FFmpeg render path | Only if Remotion becomes a bottleneck; not planned |

Rules: stream through files (no whole-video reads into RAM); temp files under `data/temporary/`; capture stderr for diagnostics; apply timeouts; validate inputs came from the asset store ([file-security](../security/file-security.md)).

## Failure modes

Missing binary once StoryWeaver-owned FFmpeg code exists (readiness check should report it — Planned); unsupported codec; very long encodes on CPU-only hardware; disk exhaustion in `data/temporary`.

## Division of labour

Remotion: frame composition and preview. FFmpeg: probing, audio finishing, packaging. See [rendering](rendering.md), [ADR-007](../decisions/ADR-007-media-rendering-strategy.md).

## Related

[media-overview](media-overview.md) · [rendering-architecture](../architecture/rendering-architecture.md)
