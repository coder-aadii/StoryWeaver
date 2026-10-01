# Subtitle System

> Presenting narration text on screen, synchronised with the audio.

## Status

**Partially implemented.** `SceneSpec.subtitle`, `TimelineScene.subtitle` and a Remotion subtitle box exist (one string per scene, displayed for the whole scene). Word-level alignment, SRT/VTT export and styling controls are **Planned — not implemented**. `AssetType.SUBTITLE` exists in the enum.

## Purpose

Provide readable, accurately-timed on-screen text derived from narration.

## Problem being solved

Per-scene blocks of text can be too long to read and out of sync with speech; accessibility and retention need proper segmentation.

## Inputs

Narration text, measured audio (and later word timestamps from forced alignment).

## Outputs

Subtitle cues on the timeline; optional exported subtitle file asset.

## Entities

`TimelineScene.subtitle`; future subtitle asset.

## Workflow (Target Architecture)

Narration → split into readable cues (character/line limits) → align with audio (forced alignment, e.g. via a Whisper-class model — **Decision pending**) → cues with start/end → rendered by the composition and/or exported ([subtitle pipeline](../media/subtitle-pipeline.md)).

## Business rules

- Subtitle text defaults to the narration (`build_timeline` uses `s.subtitle or s.narration`).
- Cue timing is derived by code from audio; the LLM never assigns timestamps.
- Lines must stay inside safe areas defined by the visual bible.

## AI responsibilities

None required (optional line-break suggestions).

## Deterministic responsibilities

Segmentation, alignment, timing, layout, export.

## Current implementation

`BasicComposition` renders the scene's `subtitle` in a bottom-centred semi-transparent box for the scene's entire duration; verified in the sample render. Nothing splits long text.

## Planned implementation

Cue splitting, alignment, styling, burn-in vs sidecar choice, multi-language.

## Edge cases

Very long narration in a 2-second scene; right-to-left scripts; overlapping cues; profanity filtering (policy pending).

## Open questions

Word-highlight ("karaoke") style; alignment tool; default styling.
