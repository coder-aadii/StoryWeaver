# Scene Data Model

> Scene storage (implemented) and the canonical scene representation (target).

## Status

**Partially implemented.** `scenes`/`scene_versions` tables, `SceneSpec`/`Timeline` Pydantic models and the deterministic `build_timeline` exist. Scenes have basic CRUD; scene versions have no API; nothing generates scenes. The richer nested scene design below is **target**, not code.

## Tables

- `scenes`: `project_id`, optional `script_id`, `sequence` (≥1 enforced by the API schema only), `status` (`draft|ready|generating|failed`), `error`. Each scene has its own identity and status so one scene can be regenerated alone.
- `scene_versions`: `scene_id`, `version`, `data` JSONB, unique `(scene_id, version)`.

## Implemented contract: `SceneSpec` (`apps/api/app/schemas/scene.py`)

```json
{
  "scene_id": "scene_001", "sequence": 1, "narration": "...",
  "duration": null,
  "visual_intent": "", "characters": [], "locations": [], "objects": [],
  "action": "", "emotion": "",
  "camera": { "shot": "wide", "movement": "slow_zoom_in" },
  "image_prompt": "", "negative_prompt": "",
  "voice": null, "music": null, "sfx": [], "subtitle": null
}
```

`shot` ∈ wide, medium, close_up, extreme_close_up, over_shoulder, aerial. `movement` ∈ static, slow_zoom_in, slow_zoom_out, pan_left, pan_right, tilt_up, tilt_down. `duration` is nullable: **set by code**, never by the LLM. `scene_id` here is a string label (e.g. `scene_001`); the DB row id is a UUID and the target design below uses an integer — the mapping is *Decision pending* (see the identifier table in [domains/storyboard-system](../domains/storyboard-system.md)).

## Timeline contract (implemented)

`TimelineScene`: `scene_id`, `start`, `duration`, `narration`, `subtitle`, `image_src`, `audio_src`, `camera`. `Timeline`: `version`, `fps` 30, `width` 1920, `height` 1080, `scenes`. Built by `build_timeline` ([timeline-specification](../media/timeline-specification.md)). Mirrored in zod in `packages/video` by hand, with both sides checked against shared sample documents ([KI-7](../reference/status.md#known-issues-and-limitations), mitigated in P0).

## Target canonical representation (Planned — not implemented)

A grouped design to replace the flat fields once generation exists:

```json
{
  "scene_id": 17, "duration": 5.4, "narration": "...",
  "visual": { "location": "", "characters": [], "subject": "", "action": "", "camera": "", "emotion": "", "time": "" },
  "image":  { "style": "", "prompt": "", "negative_prompt": "" },
  "motion": { "type": "slow_zoom", "direction": "in", "intensity": 0.15 },
  "audio": {}, "subtitle": {}
}
```

Differences from `SceneSpec`: grouped `visual`/`image`/`motion`, numeric motion intensity (`CameraSpec` has none), time-of-day, structured audio/subtitle, and an **integer** `scene_id` (`SceneSpec.scene_id` is a string). Migrating requires a `SceneSpec` v2 and a data migration of `scene_versions.data`; *Decision pending*. Duration remains determined by narration, pacing and story rhythm; 5–7 s is a typical range, not a rule ([domains/timeline-system](../domains/timeline-system.md)).

## Rules

- A change to a scene creates a new `scene_versions` row; assets reference the scene, not a version (linking assets to the version that produced them: *Decision pending*).
- Scene order = `sequence`; `build_timeline` sorts by it.
- **`scene_versions.data` is not validated on write**: no API exposes versions and no code path checks the JSON against `SceneSpec`, so the database can hold any JSON object there.

See [domains/storyboard-system](../domains/storyboard-system.md).

## Scene, shot, prompt and asset are different things (target)

Scene intent ≠ image prompt ≠ generated asset ≠ timeline shot. The canonical definition — and the table mapping `scenes.id` (UUID), `sequence`, `SceneSpec.scene_id` (string) and the target numeric id — is in [domains/storyboard-system](../domains/storyboard-system.md). Data-model consequences: only scene intent (in `scene_versions.data`) and generated assets (`assets` rows) exist as storage; the timeline shot is just `TimelineScene` (one scene = one shot). A **Shot** entity (several shots per scene reusing one image with different crops, or one image across scenes) is **not modelled** — *Decision pending*. Note the name clash: `CameraSpec.shot` in the schema is the *framing type* (`wide`, `close_up`, …), not a Shot entity. Asset versions (Image Scene 12 v1/v2) and which version a timeline used: [asset-data-model](asset-data-model.md#artifact-versions-and-dependencies-target); `renders.timeline` snapshots only the asset URLs.
