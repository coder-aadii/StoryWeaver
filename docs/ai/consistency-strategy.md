# Consistency Strategy

> How characters, style and world stay visually and narratively consistent across a video.

## Status

**Planned** — `characters` and `locations` tables exist (per project, unique name, JSONB `attributes`); no consistency mechanism is implemented. `CharacterVersion` and visual-style entities are deferred.

## Problem

Image models do not remember. Without structure, a character changes face, clothing and age between scenes, and style drifts.

## Target Architecture — layers of control

1. **Bibles as the single source of truth.** Character bible ([character-system](../domains/character-system.md)) and visual bible ([visual-system](../domains/visual-system.md)) hold canonical descriptors. Scenes reference characters by id; they never redefine them.
2. **Verbatim descriptor injection.** The prompt builder inserts the same character descriptor text into every scene containing that character ([visual-prompting](visual-prompting.md)).
3. **Reference images.** Approved character sheets / key frames stored as `REFERENCE` assets and passed to the generator (image-to-image, IP-adapter-style conditioning, LoRA, ControlNet — all depend on the chosen image backend; none implemented). See [image-consistency](../media/image-consistency.md).
4. **Fixed style parameters.** Same checkpoint/style token set, resolution and sampler settings per project, recorded in project settings.
5. **Seeds and variation policy.** Fixed seed for re-renders of an unchanged scene; new seed only on explicit regeneration.
6. **Narrative consistency.** The script stage receives a running state (who is where, what they know) and validation checks character/location names against the bibles ([script-generation](../domains/script-generation.md)).
7. **Automated checks (Future).** Vision-model or embedding-similarity comparison of generated images against references ([quality-assurance](../domains/quality-assurance.md)).

Bible entries are **referenced** by scene prompts (by id, assembled by code) instead of being re-described scene by scene — this keeps one canonical wording per character/location/style. One image can also yield several shots via zoom, pan, crop or reframe, which improves continuity (same pixels) and lowers cost ([camera-motion](../media/camera-motion.md)).

## Model role / input / prompts

LLM drafts bible entries from the story (structured output); a human can edit them. Image model consumes descriptors plus references. Input to every scene call includes only the bible entries for characters present ([context-management](context-management.md)).

## Validation, retry/fallback

Schema validation of bible entries; reject scenes referencing unknown characters; on failed image QA regenerate the single scene ([asset-generation-workflow](../workflows/asset-generation-workflow.md)). Fallback when references are unsupported by the backend: stronger textual descriptors plus fixed seed — lower fidelity, documented limitation.

## Cost and quality

Reference conditioning and LoRA training add setup cost but cut regeneration waste; decide per backend ([ai-cost-strategy](ai-cost-strategy.md)). Quality metrics: [ai-quality-evaluation](ai-quality-evaluation.md).

## Current vs future

Current: tables and `reference_asset_ids` field on `ImageRequest`. Future: everything above. Open: character versioning (age progression, costume changes) — Deferred until required by the production workflow.
