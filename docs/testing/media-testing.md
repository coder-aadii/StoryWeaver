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
- Remaining contract gaps ([KI-7](../reference/status.md#known-issues-and-limitations)): Pydantic `Timeline.fps`/`width`/`height` have no positivity constraint (zod requires > 0), so those cases are not in the shared samples; `zod` is pinned to Remotion's required 4.5.4 (exact, no `^`).

## Python↔zod timeline contract (automated since P0)

`scripts/export_schemas.py` (via `make schemas`) writes the JSON Schema **and** canonical valid/invalid sample documents to `packages/schemas/samples/`. Two tests consume the same files:

- `apps/api/tests/test_timeline_contract.py` — Pydantic must accept every valid sample (and produce the recorded normalised form) and reject every invalid one.
- `packages/video/src/contract.test.ts` — the zod `timelineSchema` must do the same.

A change to only one side therefore fails `make test` (checked with deliberate one-sided breaks during P0). After changing `apps/api/app/schemas/scene.py` or `packages/video/src/types.ts`: run `make schemas`, review the diff of `packages/schemas/`, update `packages/video/sample/timeline.json` if the shape changed, then run `make test` and `make render-sample`. Fixture and render-path details: [ADR-009](../decisions/ADR-009-render-asset-resolution.md).
- Frame-level checks (non-black, subtitle region), audio loudness/clipping, A/V sync: see [quality architecture](../architecture/quality-architecture.md), [QA workflow](../workflows/qa-workflow.md).

Renders are slow and need a headless Chrome (Remotion downloads it and bundles its own FFmpeg; system FFmpeg is not required), so they would belong in a separate, opt-in gate ([quality gates](quality-gates.md)).
