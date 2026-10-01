# Media Testing

> Testing the deterministic media pieces.

## Status

Partially implemented (timeline/camera logic and one manual render). No automated render or media QA.

## Automated

- Python `build_timeline`/`estimate_duration` ([unit testing](unit-testing.md)).
- `packages/video/src/camera.test.ts` (counts: [testing strategy](testing-strategy.md#layers)): zoom endpoints and clamping (`slow_zoom_in` at progress 0, 1 and beyond), `static` does not move, and `sample/timeline.json` parses with the zod `timelineSchema`.
- `MockImageGenerator` returns a small valid-looking PNG; not asserted by a test yet.

## Manual verification performed during foundation

`make render-sample` produced a 6.5 s, 1280×720, 30 fps H.264 MP4 (195 frames); a frame was inspected visually for placeholder, camera transform and subtitle.

## Planned — not implemented

- Render smoke test in automation (render 1 s, `ffprobe` duration/resolution/codec).
- Python↔zod `Timeline` contract test (schema export diff) — none exists today ([KI-7](../reference/status.md#known-issues-and-limitations)); known differences: `camera` is required in zod but defaults in Python, and `camera.shot` is a free string in zod but a fixed set in Python.

## Manual contract-drift check (not automated)

After changing `apps/api/app/schemas/scene.py` or `packages/video/src/types.ts`:

1. `make schemas` and review the diff of `packages/schemas/timeline.schema.json`.
2. Compare it field by field with `timelineScene`/`timelineSchema` in `types.ts`: names, required vs defaulted, enums (`CameraMovement`, `ShotType`), numeric constraints.
3. Update `packages/video/sample/timeline.json` if the shape changed, then run `make test-web` and `make render-sample`.

This is a review procedure, not a gate.
- Frame-level checks (non-black, subtitle region), audio loudness/clipping, A/V sync: see [quality architecture](../architecture/quality-architecture.md), [QA workflow](../workflows/qa-workflow.md).

Renders are slow and need a headless Chrome (Remotion downloads it and bundles its own FFmpeg; system FFmpeg is not required), so they would belong in a separate, opt-in gate ([quality gates](quality-gates.md)).
