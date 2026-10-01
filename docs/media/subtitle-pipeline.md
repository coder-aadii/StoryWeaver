# Subtitle Pipeline

> How on-screen subtitles and subtitle files are produced.

## Status

**Partially implemented** — one caption per scene in the Remotion composition. No timed word/line segmentation, no alignment, no subtitle file export.

## Current implementation

- `SceneSpec.subtitle` (optional) and `TimelineScene.subtitle`. `build_timeline` sets `subtitle = scene.subtitle or scene.narration` — i.e. the whole narration as one caption.
- [`BasicComposition.tsx`](../../packages/video/src/BasicComposition.tsx) renders `scene.subtitle` in a dark rounded box at the bottom for the entire scene duration. No wrapping rules beyond CSS `maxWidth: 80%`, no styling configuration, no language/RTL handling.
- `AssetType.SUBTITLE` exists; no subtitle assets are generated. No SRT/VTT export (ingestion of SRT/VTT as *sources* is also not implemented).

## Target Architecture

1. **Segmentation (code):** split narration into readable cues (max characters per line, max lines, reading speed e.g. ≤ ~17 cps — value Decision pending), breaking at punctuation.
2. **Timing:** distribute cues across the scene by measured audio duration; improve with forced alignment or TTS word timestamps (Future). Cue times are scene-relative and converted to absolute by the timeline.
3. **Render:** composition draws cue-by-cue; style (font, size, outline, position, safe area) comes from project/visual settings.
4. **Export:** optional `.srt`/`.vtt` asset generated from the same cues, for upload alongside the MP4.
5. **Validation (Future QA):** cue overlap, off-screen text, subtitle ≠ narration mismatch ([quality-assurance](../domains/quality-assurance.md)).

Subtitle text is derived from narration by code; the LLM does not set cue timestamps ([ADR-004](../decisions/ADR-004-ai-vs-deterministic-responsibilities.md)).

## Failure modes

Long narration overflowing the box; mismatch after narration edits (regenerate cues when narration hash changes); font missing on the render machine.

## Open questions

Burned-in vs sidecar default; multi-language subtitles; karaoke-style highlighting.

## Related

[subtitle-system](../domains/subtitle-system.md) · [voice-pipeline](voice-pipeline.md) · [timeline-specification](timeline-specification.md)
