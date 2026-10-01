# ADR-009: Render asset resolution via a per-render Remotion public dir

> How generated images and audio reach the Remotion renderer: project-relative asset keys resolved with `staticFile()` against `--public-dir`.

## Status

Accepted · 2026-10-01 · **Partially implemented** — the mechanism is proven by a fixture render (P0-T7) and available as the `Assets` composition; the real render workflow, Timeline v2 and asset staging are Planned (P8). Resolves the asset-resolution part of [KI-17](../reference/status.md#known-issues-and-limitations). Confirms decision D12 of the [implementation plan](../../implementation-plan/IMPLEMENTATION_PLAN.md).

## Context

`BasicComposition` used `<Img src={scene.image_src}>` directly. That works for URLs but there is no route serving `data/`, and a headless browser cannot be assumed to load arbitrary local file paths, so generated images and WAVs had no defined way into a render. The sample render only worked because it had no assets.

## Decision

1. Timelines reference assets by **project-relative keys** (`images/scene_001.png`, `audio/scene_001.wav`), never absolute paths or localhost URLs.
2. A render stages the keys it needs into a **per-render directory** and passes it to the CLI with `--public-dir`. The composition resolves keys with Remotion's `staticFile()`.
3. `http(s):`, `data:` and `/`-prefixed references are passed through unchanged (`publicDirAsset` in `packages/video/src/BasicComposition.tsx`). The web Player keeps using `rawAsset` (references used as given) with URLs from the API.
4. The existing `Basic` composition is unchanged in behaviour; a second composition `Assets` (same schema) uses the public-dir resolver. Both are produced by `createComposition(resolver)`.

## Evidence (fixture render, 2026-10-01)

Procedure: `pnpm --filter @storyweaver/video spike:assets -- --out <dir> [--perf]` (script `packages/video/scripts/spike-assets.mjs`; not part of `make test`). It regenerates a deterministic fixture (`scripts/make-fixture.mjs`: a 320×180 four-colour PNG and a 2.0 s 16 kHz sine WAV; the WAV is git-ignored by the repo's `*.wav` rule, so it is regenerated, byte-identical, on each run), renders the `Assets` composition with `--public-dir sample/fixture`, and verifies the MP4 using **only the ffmpeg/ffprobe bundled with Remotion** (no system FFmpeg):

| Check | Result |
| --- | --- |
| Video stream | h264, 1280×720, 30/1 |
| Container duration | 3.0507 s vs 3.0 s timeline (AAC padding; tolerance 0.1 s) |
| Audio stream | aac, 48 kHz, present |
| Frame at 1.0 s | all four quadrant colours within 1 unit of the fixture PNG (static camera) |
| Frame at 2.5 s (scene without image) | does not show the fixture |
| Audio | non-silent for ≈2.1 s (WAV is 2.0 s), starting at 0 s, ending at ≈2.0 s |

Measurement (one run, 8-thread CPU-only laptop, headless Chrome, default concurrency; **a measurement, not a promise**): a 60 s timeline of 30 scenes (1800 frames, 1280×720, six camera movements, audio per scene) rendered in **36.6 s wall-clock (≈1.64× realtime)**, 2.7 MiB; the 3 s fixture rendered in 5.0–6.6 s including bundling.

## Alternatives considered

- **Local HTTP route serving `data/`** (`GET /assets/{id}/content`): needed anyway for Studio preview (planned in P6), but for rendering it adds a running API dependency, auth/CORS concerns and makes render inputs mutable while rendering. Rejected for render.
- **`file://` URLs:** depend on Chrome security flags; not tested; rejected.
- **Inlining assets as `data:` URIs in the props:** large timelines and slow props serialisation; rejected.

## Consequences

- Staging (copy or hard-link the keys a render needs) is new work in P8; per-render directories make a render immutable with respect to later scene regeneration.
- Timeline v1 (`image_src`/`audio_src` strings) is already compatible: the same field holds a key. No Python change is needed to use this mechanism.
- **Version warning found and fixed:** Remotion reported `zod: installed 4.6.5, required 4.5.4`. After the spike, `zod` was pinned to exactly `4.5.4` in `packages/video` and `apps/web` (lockfile updated) and the warning no longer appears. Keep the pin exact when upgrading Remotion.
- AAC adds ~50 ms of padding to container duration; QA tolerances (P8) must allow it.

## Timeline v2 field proposal

For [P8](../../implementation-plan/06-timeline-render-qa.md) (authoritative detail there; this lists what the spike implies):

| Field | Purpose |
| --- | --- |
| `version: 2` | Union with v1; `normalizeTimeline()` maps v1 → v2 |
| `fps`, `width`, `height` | As v1 (integers > 0) |
| integer **frame** times (`start_frame`, `duration_frames`) | Source of truth; seconds derived. Avoids float accumulation |
| `duration_source: "measured" \| "estimated"` | Final renders refuse `estimated` ([KI-16](../reference/status.md#known-issues-and-limitations)) |
| `assets: { key → { sha256, bytes, mime } }` | Content-addressed manifest; makes `timeline_hash` pin asset content |
| per scene `shots[]` with crop rects, `audio { key, offset_frames }`, `subtitle cues[]` | Deterministic shot/crop and caption data computed by code |
| asset keys | project-relative, `[A-Za-z0-9._/-]` only, no `..`, derived from asset ids |

## Revisit when

Remotion's licensing or CLI changes; staging cost becomes significant for large projects; or Studio preview and render converge on one asset route.
