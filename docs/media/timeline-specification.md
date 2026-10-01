# Timeline Specification

> The contract between scene planning and rendering: Timeline JSON, how it is built, and the canonical target scene shape.

## Status

**Implemented** (current `Timeline` schema, deterministic builder and Remotion consumer; consistent with [status](../reference/status.md)) with known limitations below — the richer canonical scene design is **Planned**. The canonical scene design below is **Target Architecture**.

## Current implementation

Python source of truth: [`schemas/scene.py`](../../apps/api/app/schemas/scene.py). Mirrors: zod in [`packages/video/src/types.ts`](../../packages/video/src/types.ts), generated `packages/schemas/timeline.schema.json` ([schemas reference](../reference/schemas.md)).

`Timeline`: `version` (1), `fps` (30), `width` (1920), `height` (1080), `scenes[]`; property `duration_seconds` = max(start+duration).

`TimelineScene`: `scene_id`, `start` (≥0), `duration` (>0), `narration`, `subtitle`, `image_src`, `audio_src`, `camera {shot, movement}`.

`SceneSpec` (what AI plans): `scene_id` (string), `sequence`, `narration`, optional `duration` ("set by code"), `visual_intent`, `characters`, `locations`, `objects`, `action`, `emotion`, `camera`, `image_prompt`, `negative_prompt`, `voice`, `music`, `sfx[]`, `subtitle`.

### Deterministic builder ([`video/timeline.py`](../../apps/api/app/video/timeline.py))

`build_timeline(scenes, fps=30)`: sort by `sequence`; duration = `scene.duration` if present, else `estimate_duration(narration)`; `start` = running sum (rounded to ms); subtitle = `scene.subtitle or narration`. It does **not** populate `image_src`/`audio_src` (asset resolution is Planned) and does not add transitions or gaps.

`estimate_duration`: words ÷ `WORDS_PER_SECOND` (2.5, ≈150 wpm) clamped to `[MIN_SCENE_SECONDS=2.0, MAX_SCENE_SECONDS=7.0]`, rounded to ms. This is a **fallback estimate**. Measured narration length must override it once voice generation exists ([voice-pipeline](voice-pipeline.md)). **Limitation:** because of the 7 s cap, narration longer than about 17 words (e.g. a 40-word line needing ~16 s) is assigned 7 s, so subtitles and any audio longer than the scene would be cut off; the estimate must not be used for a final render ([KI-16](../reference/status.md#known-issues-and-limitations)).

**Who owns duration:** `SceneSpec.duration` is optional because **deterministic code assigns it** (measured audio, else the estimator); an LLM never supplies durations or start times.

### Duration is a pacing decision, not a rule

5–7 seconds per image is a typical target, **not a hard rule**. Duration should reflect narration length, pacing, visual complexity, the emotional beat, transitions and story rhythm. A reveal may hold 9 s; a rapid montage may use 1.5 s shots. The 2–7 s clamp in code is only the estimator's default bound and will be replaced by narration-driven timing plus pacing rules (Planned). Long narration should split into more shots rather than hold one still (see Shots below).

Tests: `test_timeline_is_deterministic_and_contiguous` ([`test_units.py`](../../apps/api/tests/test_units.py)); in `packages/video`, `camera.test.ts` parses `sample/timeline.json` with the zod schema.

## Target Architecture — canonical scene (not implemented)

```json
{
  "scene_id": 17,
  "duration": 5.4,
  "narration": "...",
  "visual": {
    "location": "...", "characters": [], "subject": "...",
    "action": "...", "camera": "...", "emotion": "...", "time": "..."
  },
  "image": { "style": "...", "prompt": "...", "negative_prompt": "..." },
  "motion": { "type": "slow_zoom", "direction": "in", "intensity": 0.15 },
  "audio": {},
  "subtitle": {}
}
```

Differences from today's `SceneSpec`: nested `visual`/`image`/`motion`/`audio`/`subtitle` objects instead of flat fields; numeric `scene_id` vs current string; `motion` with a continuous `intensity` and direction instead of the `camera.movement` enum (current renderer uses fixed intensities, [camera-motion](camera-motion.md)); structured `audio`/`subtitle` objects instead of free strings. Migrating requires a schema version bump (`SceneVersion.data` is JSONB, so stored versions can coexist) — **Decision pending**. Domain description: [scene-data-model](../data/scene-data-model.md), [storyboard-system](../domains/storyboard-system.md).

### Shots (Target)

Scene intent, image prompt, generated asset and timeline shot are distinct (canonical: [storyboard-system](../domains/storyboard-system.md#separate-concepts-intent--prompt--asset--shot)). Do not confuse the future Shot entity with `CameraSpec.shot`, which is today only a framing-type label (wide, close_up, …). A scene may contain several shots; a shot references an image asset (possibly reused) and a camera move over a time range. No `Shot` type exists in the schema today; adding one is a timeline schema change.

## Validation rules (Target; none beyond schema types today)

No overlapping or negative starts; contiguous or intentionally gapped scenes; every `image_src`/`audio_src` resolves to a READY asset; total duration equals max end; fps/size within supported presets; audio length ≤ scene duration (or scene extended by code). Failing validation blocks render ([render-workflow](../workflows/render-workflow.md)).

## Extension points / failure modes

Add fields to Python and zod together and regenerate JSON Schema (`make schemas`); drift between the two mirrors is the main risk and already exists (`camera` required vs defaulted, `shot` free string vs fixed set — [KI-7](../reference/status.md#known-issues-and-limitations)). A contract test is Planned. Asset resolution (`image_src`/`audio_src` → fetchable URLs) is also unresolved ([KI-17](../reference/status.md#known-issues-and-limitations)). Three resolutions coexist unreconciled: `ImageRequest` 1344×768, sample timeline 1280×720, `Timeline` default 1920×1080. Rounding: Remotion converts seconds to frames with `Math.round`, so sub-frame error accumulates per scene boundary but does not drift (each start is rounded independently).

## Related

[remotion](remotion.md) · [timeline-system](../domains/timeline-system.md) · [rendering](rendering.md)
