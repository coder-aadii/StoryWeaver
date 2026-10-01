# Remotion

> The Remotion package: compositions, preview and rendering from Timeline JSON.

## Status

**Implemented** (foundation) — one composition (`Basic`), Player preview, CLI render verified. Not a full editor.

## Current implementation

Package `@storyweaver/video` in [`packages/video`](../../packages/video):

| File | Purpose |
| --- | --- |
| `src/types.ts` | zod `timelineSchema` (hand-maintained mirror of Python `Timeline`; known differences below) |
| `src/camera.ts` | `cameraTransform(movement, t)` ([camera-motion](camera-motion.md)) |
| `src/BasicComposition.tsx` | `BasicComposition` + `timelineDurationInFrames` |
| `src/Root.tsx` | registers `<Composition id="Basic">` with `schema`, `defaultProps`, and `calculateMetadata` (duration, fps, width, height from props) |
| `src/entry.ts` | `registerRoot` for CLI/Studio |
| `src/index.ts` | exports for the web app (`BasicComposition`, `timelineSchema`, `sampleTimeline`, …) |
| `sample/timeline.json` | 3-scene 1280×720 sample |

`BasicComposition` per scene: gradient background (hue by index), the image (`<Img>` if `image_src`, else a dashed "Image placeholder · scene_id" box), camera transform, `<Audio>` if `audio_src`, bottom subtitle box. Scenes are `<Sequence from=round(start·fps) durationInFrames=round(duration·fps)>`.

**Verified:** `make render-sample` (`remotion render src/entry.ts Basic out/sample.mp4 --props=./sample/timeline.json`) produced a 195-frame, 6.5 s, 1280×720, 30 fps H.264 file; a frame showed placeholder + subtitle. Output `packages/video/out/` is git-ignored. First render downloads a headless Chrome. **Preview:** `pnpm --filter @storyweaver/video studio` and the `/studio` page's `<Player>` ([studio](../frontend/studio.md)). Unit tests: camera function and sample-schema parse (`vitest`).

## Responsibilities

Remotion: layout, motion, sequencing, visual subtitle drawing, frame rendering/encoding. It does **not** decide timing, fetch assets, call AI, or mutate the database; it is a pure function of Timeline JSON (+ static files).

## Target Architecture

- Asset URLs in the timeline resolve to files served to the renderer (local `file`/HTTP, `staticFile`); the render workflow supplies a resolved, validated timeline ([render-workflow](../workflows/render-workflow.md)). **Current limitation / Decision pending — asset serving:** no route or static server exposes `data/`, `build_timeline` leaves `image_src`/`audio_src` empty, and `BasicComposition` passes `image_src` straight to `<Img src>`. A generated image therefore cannot appear in the `/studio` Player or be fetched by the renderer today; the sample render works only because it has no images ([KI-17](../reference/status.md#known-issues-and-limitations), [KI-16](../reference/status.md#known-issues-and-limitations)).
- Additional compositions (title card, lower-thirds, end card) and shared components ([adding-a-remotion-composition](../development/adding-a-remotion-composition.md)).
- Subtitle cues, transitions, audio tracks per [subtitle-pipeline](subtitle-pipeline.md), [transitions](transitions.md), [music-and-sfx](music-and-sfx.md).
- Render invoked programmatically (`@remotion/renderer`) from a worker, with progress reporting.
- Concurrency tuned for a 16 GB laptop; avoid parallel renders.

## Known drift between the zod mirror and Python ([KI-7](../reference/status.md#known-issues-and-limitations))

| Field | Python (`schemas/scene.py`) | zod (`types.ts`) |
| --- | --- | --- |
| `TimelineScene.camera` | optional, defaults to `CameraSpec()` | **required** (no default on the object) |
| `camera.shot` | fixed set (`wide`, `medium`, `close_up`, …) | free `string` |

No test compares the two; only the sample timeline is parsed by zod. A contract test (generate sample timelines from Python, parse with zod, and compare JSON Schema) is **Planned — not implemented**.

## Failure modes

Missing/blocked asset URL (`<Img>` error); chrome download failure offline; out-of-memory on long 1080p renders; schema drift between zod and Python.

## Licensing

Remotion requires a company license above a size threshold; the Player prints a reminder until `acknowledgeRemotionLicense` is set. That choice is intentionally left to the project owner ([README](../../README.md)).

## Related

[timeline-specification](timeline-specification.md) · [rendering](rendering.md) · [rendering-architecture](../architecture/rendering-architecture.md)
