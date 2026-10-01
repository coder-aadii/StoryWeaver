# Voice and Audio

> Narration, music and sound effects — generated or selected, then mixed deterministically.

## Status

**Partially implemented — interface only.** `VoiceProvider` ABC and `UnconfiguredVoiceProvider` (fails loudly with `ProviderNotConfiguredError`) exist. **No TTS engine, music/SFX handling, mixing, ducking or loudness normalization is implemented.** Remotion plays an `<Audio>` only if a scene has `audio_src`.

## Purpose

Give each video a consistent narrator and a mixed soundtrack whose timing drives the timeline.

## Problem being solved

Narration length determines scene duration; inconsistent voices or uncontrolled loudness make videos feel amateur.

## Inputs

Script/scene narration, voice choice, music/SFX selections.

## Outputs

Audio `Asset`s (types `voice`, `audio`, `music`, `sfx`) under `data/audio/`, `data/music/`, `data/sfx/`; measured durations; mixed track at render time.

## Entities

`Asset`, `SceneSpec.voice/music/sfx` (free strings today).

## Workflow (Target Architecture)

Per scene: `VoiceProvider.synthesize(text, voice=…)` → `VoiceResult(data, mime_type, duration_seconds)` → store asset → duration feeds the timeline ([timeline system](timeline-system.md)). Music/SFX selected or generated, then mixed at render ([FFmpeg](../media/ffmpeg.md), [voice pipeline](../media/voice-pipeline.md), [music and SFX](../media/music-and-sfx.md)).

## Business rules

- **Voice consistency (Target):** one narrator voice per project unless the script requires otherwise; where the voice id is stored is Decision pending (`Project.settings` has no defined keys; today only the free-string `SceneSpec.voice` exists).
- **Duration is measured from audio**, never guessed by an LLM (documented in the `VoiceResult` contract). Wiring `VoiceResult.duration_seconds` into `SceneSpec.duration`/the timeline is **Planned** — nothing does it today ([KI-16](../reference/status.md#known-issues-and-limitations)).
- Mixing rules (**Planned — not implemented**): music ducking under narration, loudness normalization to a target LUFS (value Decision pending), clipping prevention, fades.
- TTS must be lazy-loaded; no model is loaded at API startup.

## AI responsibilities

Speech synthesis (Piper, Kokoro, XTTS-class, cloud — all candidates, none chosen); optional music/SFX suggestion.

## Deterministic responsibilities

Duration measurement, file storage, synchronisation with timeline, mixing parameters, normalization, QA of levels.

## Current implementation

Interface + unconfigured provider; `get_voice_provider()` always returns the unconfigured one.

## Planned implementation

First local TTS adapter, per-scene voice assets and regeneration, music/SFX library, mix at render, audio QA ([quality assurance](quality-assurance.md)).

## Edge cases

Very long sentences (split before TTS); numerals/names pronunciation; silence padding between scenes; sample-rate mismatches; licensing of music assets (content policy).

## Open questions

TTS engine; stock vs generated music; where the mix is performed (Remotion audio layers vs FFmpeg post-mix).
