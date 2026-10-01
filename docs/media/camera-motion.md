# Camera Motion

> How still images are animated with deterministic camera moves.

## Status

**Implemented** (basic) — six moving presets plus `static`, with fixed intensities. Variable intensity/direction, easing choices, multi-shot per image and focal-point targeting are **Planned**.

## Current implementation

Schema: `CameraSpec {shot, movement}` with `shot ∈ wide, medium, close_up, extreme_close_up, over_shoulder, aerial` and `movement ∈ static, slow_zoom_in, slow_zoom_out, pan_left, pan_right, tilt_up, tilt_down` ([`schemas/scene.py`](../../apps/api/app/schemas/scene.py)). The zod mirror uses the same `shot` and `movement` enums (a Python test compares the literals; previously `shot` was a free string — KI-7, mitigated in P0).

Implementation: pure function `cameraTransform(movement, t)` in [`camera.ts`](../../packages/video/src/camera.ts), `t` = scene progress clamped to [0,1], **linear** (no easing):

| Movement | scale | x (% of frame) | y (%) |
| --- | --- | --- | --- |
| static | 1 | 0 | 0 |
| slow_zoom_in | 1 → 1.12 | 0 | 0 |
| slow_zoom_out | 1.12 → 1 | 0 | 0 |
| pan_left | 1.12 | +3 → −3 | 0 |
| pan_right | 1.12 | −3 → +3 | 0 |
| tilt_up | 1.12 | 0 | +3 → −3 |
| tilt_down | 1.12 | 0 | −3 → +3 |

Applied in `BasicComposition` as CSS `scale(...) translate(x%, y%)` on the image layer. Because pans and tilts use 1.12 scale, edges never show blank space. `shot` is carried in data but **does not affect rendering**. Unit tests ([`camera.test.ts`](../../packages/video/src/camera.test.ts)) check only the `slow_zoom_in` end points (progress 0 and 1), clamping of progress above 1, and that `static` does not move; monotonicity and the pan/tilt/zoom-out presets are not tested.

## Design intent

Motion adds life to stills and conveys emotion (slow push-in for tension, pull-out for reveal, pans to follow action). It is chosen by the storyboard stage (AI proposes a type from a closed set) and executed by code. Camera moves must be deterministic functions of progress so renders are reproducible ([ADR-007](../decisions/ADR-007-media-rendering-strategy.md)).

## Target Architecture

- `motion {type, direction, intensity}` as in the canonical scene ([timeline-specification](timeline-specification.md)), with code clamping intensity to safe crop limits.
- **One image, several shots:** different crops/zoom regions/moves from the same asset, reducing image generation cost and improving continuity ([ai-cost-strategy](../ai/ai-cost-strategy.md)). Requires a shot concept (not present).
- Focal point (x,y) from the scene so zooms target the subject.
- Easing curves (ease-in-out) and subtle parallax if layered assets exist (Future).
- Composition guidance: generate images slightly wider than final framing and keep subjects away from edges and the subtitle area ([visual-prompting](../ai/visual-prompting.md)).
- Motion must not exceed the source resolution. Three resolutions exist and are **not reconciled**: the `ImageRequest` default is 1344×768, the sample timeline is 1280×720, and the `Timeline` default is 1920×1080. Zooming a 1344×768 image into a 1920×1080 frame upscales it; quality impact is unmeasured — Decision pending on generation resolution.

## Failure modes

Blurry upscaling at high zoom; subject cropped by pan; motion sickness from fast movement (keep intensities low); mismatch between declared `shot` and actual framing.

## Related

[transitions](transitions.md) · [remotion](remotion.md) · [image-pipeline](image-pipeline.md)
