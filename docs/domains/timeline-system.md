# Timeline System

> The deterministic, machine-readable description of what appears and sounds when — the contract between the AI-authored content and the renderer.

## Status

**Implemented.** (Minimal scope.) `Timeline`/`TimelineScene` schemas, `build_timeline` and `estimate_duration` exist and are tested; the Remotion `Basic` composition consumes the JSON. Transitions, multi-shot scenes, audio tracks beyond one `audio_src`, and persistence of timelines are not implemented. The `renders.timeline` JSONB column exists to snapshot a timeline per render (unused).

## Purpose

Resolve scene content into concrete start times and durations so rendering is repeatable.

## Problem being solved

LLMs are unreliable at timing. Code must own durations ([ADR-004](../decisions/ADR-004-ai-vs-deterministic-responsibilities.md)).

## Inputs

`SceneSpec[]`, measured audio durations (future), asset paths.

## Outputs

`Timeline { version, fps=30, width=1920, height=1080, scenes[] }`; each `TimelineScene { scene_id, start, duration, narration, subtitle, image_src, audio_src, camera{shot, movement} }`. Specification: [timeline specification](../media/timeline-specification.md). JSON Schema is exported to `packages/schemas/timeline.schema.json`; a zod mirror lives in `packages/video/src/types.ts`.

## Entities

Pydantic models only (no table); `Render.timeline` snapshot.

## Workflow

`build_timeline(scenes)`: sort by `sequence`; for each scene use `duration` if provided, else `estimate_duration(narration)`; `start` = cumulative sum; return the timeline. Total = max(start + duration).

## Business rules — timing

- **5–7 s is a typical target for a visual beat, not a rule.** Duration depends on narration length, pacing, visual complexity, emotional beat, transition and story rhythm. The code's fallback estimator clamps to 2–7 s at 2.5 words/second (`MIN/MAX_SCENE_SECONDS`, `WORDS_PER_SECOND`); that is an **estimate used only when real audio duration is unknown**, and an explicitly supplied `duration` is *not* clamped. **Limitation ([KI-16](../reference/status.md#known-issues-and-limitations)):** the 7 s cap silently truncates narration that needs longer (a 40-word line needs ~16 s but is assigned 7 s), so the fallback is for placeholders/previews and must not drive a final render; `build_timeline` also leaves `image_src`/`audio_src` empty, so no scene-to-asset linkage is produced.
- Measured audio duration always wins over estimates.
- Scenes are contiguous (no gaps/overlaps) in the current builder; overlap for transitions is a planned change.
- Timelines should be validated by schema before rendering. Today the zod schema is declared on the Remotion `Composition` and parsed by the web Studio; that the CLI render path (`--props`) validates it is **unverified**. The zod and Pydantic definitions are hand-maintained but checked against the same sample documents ([KI-7](../reference/status.md#known-issues-and-limitations), mitigated in P0).

## AI responsibilities

None. (AI may express pacing *intent*, e.g. "linger", which code converts to numbers — Decision pending.)

## Deterministic responsibilities

Everything: ordering, durations, start times, frame rounding (`round(seconds × fps)`), validation.

## Current implementation

See Status. Tests: `test_timeline_is_deterministic_and_contiguous`. `timelineDurationInFrames` in the video package computes composition length.

## Planned implementation

Shots within scenes (no `Shot` entity yet), transitions, audio layers (voice/music/SFX), subtitle cues, timeline persistence/versioning, validation of asset existence.

## Edge cases

Zero/negative durations (rejected by schema `gt=0`); rounding accumulation; scenes with missing images (placeholder rendered); extremely long scenes.

## Open questions

Shot model; transition overlap semantics; timeline version migration strategy (`version` field exists).
