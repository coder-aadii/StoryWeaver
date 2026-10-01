# Visual System (Visual Bible)

> The single source of truth for how a video looks, so every scene is visually consistent without re-describing style each time.

## Status

**Partially implemented (tables only).** The `locations` table (per project, `attributes` JSONB) and project `settings` JSONB exist; the visual bible itself is **Planned — not implemented**. There is no visual-style entity, no era/environment/object model, no API or UI for any of it. Style, era and object entities are **Deferred until required by the production workflow**.

## Purpose

Define global and per-project visual rules once and reference them from scenes and prompts.

## Problem being solved

Without a bible, each image prompt describes style ad hoc and the video looks like unrelated pictures. The system must avoid dependence on AI video and still feel like one professionally edited piece.

## Inputs

Story tone and genre, user style choice, optional reference images.

## Outputs

A visual bible (structured) that [visual prompting](../ai/visual-prompting.md) injects into every image prompt and QA reads when checking style.

## Entities (Target Architecture)

| Part | Content |
| --- | --- |
| Global art style | e.g. 2D illustration, simple drawings (stickman-like), cinematic illustration — **configurable, none hard-coded** |
| Illustration & line style | line quality/weight, shading, texture |
| Colour language | palette, mood-to-colour mapping |
| Lighting | time-of-day conventions, contrast |
| Environments | recurring `Location`s and their descriptions |
| Camera language | preferred shots, motion vocabulary ([camera motion](../media/camera-motion.md)) |
| Aspect ratio / composition | frame size (Timeline defaults 1920×1080), safe areas for subtitles |
| Continuity rules | what must not change between scenes |
| Negative prompts | global exclusions |
| References | `Asset` rows of type `reference` |
| Consistency rules | how characters/objects are kept stable ([consistency strategy](../ai/consistency-strategy.md)) |

Where it lives (project `settings` JSON vs dedicated tables): **Decision pending** — options and the target data model are in the [story data model](../data/story-data-model.md). `settings` has no defined keys today and `characters.attributes` has no defined schema.

## Workflow

Choose style → (AI proposes) bible → user edits → locked per project → scenes reference canonical definitions by name/id → prompts assembled from bible fragments + scene intent. Changing the bible after images exist flags affected scenes for regeneration.

## Business rules

- Scenes **reference** canonical definitions; they do not re-describe them.
- A visual answers "what does the viewer need to see at this point in the story?" — see [storyboard system](storyboard-system.md).
- Style is data; swapping style must not require code changes.

## AI responsibilities

Propose style, palette, location descriptions; write prompt fragments.

## Deterministic responsibilities

Storage, reference resolution, prompt assembly from fragments, resolution/aspect enforcement, QA thresholds.

## Current implementation

`Location` table; `ImageRequest` supports `width`/`height` (default 1344×768) and `negative_prompt`; Remotion defaults to 1920×1080 (sample uses 1280×720). Nothing connects them.

## Planned implementation

Bible schema, UI in [Studio](../frontend/studio.md), reference management, consistency conditioning ([image consistency](../media/image-consistency.md)).

## Edge cases

Style change mid-project; mixed realistic/abstract content; vertical (9:16) outputs; accessibility contrast.

## Open questions

Bible storage; per-scene overrides; whether style presets ship with the product.
