# Voice Pipeline

> How narration audio will be generated, measured and attached to scenes.

## Status

**Partially implemented** — abstraction only. No TTS engine is integrated.

## Current implementation ([`voice/base.py`](../../apps/api/app/voice/base.py))

- `VoiceProvider` ABC: `is_configured()`, `synthesize(text, *, voice=None) -> VoiceResult`.
- `VoiceResult(data, mime_type, duration_seconds)`; the duration is documented as **measured by code from the audio**, never guessed by an LLM.
- `UnconfiguredVoiceProvider` always raises `ProviderNotConfiguredError("no voice provider configured")`; `get_voice_provider()` always returns it. No settings exist for voice selection yet; `SceneSpec.voice` is a free-text optional field with no defined vocabulary or consumer.
- `AssetType.VOICE`/`AUDIO` exist; no voice assets are created.
- Candidate engines named in the product vision (Piper, Kokoro, XTTS-class, cloud) are **not integrated**; none is chosen (Decision pending). Local TTS must not be mandatory for boot.

## Target Architecture

1. Per scene, take `narration` text (after pronunciation/normalisation cleanup — Planned).
2. `synthesize` → write `data/audio/...` → compute actual duration (decode header/probe) → store as `VOICE` asset with `duration_seconds` in metadata.
3. Timeline builder reads measured duration and prefers it over the word-count estimate ([timeline-specification](timeline-specification.md)); add padding/pauses by rule (e.g. inter-scene breathing room) in code.
4. Voice consistency: one voice id per project (project settings), fixed speaking rate; same provider/voice across scenes to avoid timbre shifts ([voice-and-audio](../domains/voice-and-audio.md)).
5. Regeneration: `generate_voice(scene_id)` is idempotent per `(scene, narration hash, voice)`; changed narration invalidates audio and triggers re-timing of the timeline only.
6. Subtitle alignment from audio: forced alignment or TTS timestamps — Future ([subtitle-pipeline](subtitle-pipeline.md)).

## Failure modes

Engine not installed → asset `FAILED` with error, scene retryable; clipped/silent audio (QA check, Planned); long narration producing a scene far beyond the typical visual duration (split the scene in storyboard, not by stretching); mispronounced names (pronunciation lexicon — Future).

## Cost and performance

Local TTS on CPU is slower than real time for some engines; generate in the background, lazily load models, and cache by content hash ([ai-cost-strategy](../ai/ai-cost-strategy.md)).

## Open questions

Which engine first; SSML/pronunciation support; multi-voice (dialogue) support; licensing of voice models.

## Related

[music-and-sfx](music-and-sfx.md) · [voice-and-audio](../domains/voice-and-audio.md) · [provider-architecture](../architecture/provider-architecture.md)
