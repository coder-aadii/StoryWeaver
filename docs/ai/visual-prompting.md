# Visual Prompting

> How scene intent becomes image-generation prompts.

## Status

**Planned** — `SceneSpec.image_prompt` / `negative_prompt` fields exist; nothing generates or uses them.

## Current implementation

`SceneSpec` ([`schemas/scene.py`](../../apps/api/app/schemas/scene.py)) carries `visual_intent`, `characters`, `locations`, `objects`, `action`, `emotion`, `camera` (shot + movement), `image_prompt`, `negative_prompt`. `ImageRequest` ([`visual/base.py`](../../apps/api/app/visual/base.py)) takes `prompt`, `negative_prompt`, `width`, `height`, `seed`, `reference_asset_ids`. No prompt builder exists.

## Four distinct things (do not conflate)

Scene intent, image prompt, generated asset and timeline shot are four different things; the canonical definition is in [storyboard-system](../domains/storyboard-system.md#separate-concepts-intent--prompt--asset--shot). For prompting this means: the prompt is *built* from stored intent plus the bibles, so an image can be regenerated without changing the scene's narrative meaning. **No `Shot` entity exists today** (`SceneSpec` and `TimelineScene` are 1 scene = 1 timed block; note `CameraSpec.shot` is the *framing type*, a different thing from a future Shot entity) — shots are Planned ([timeline-specification](../media/timeline-specification.md)).

The guiding question for every visual is: *what does the viewer need to see right now?* — visuals serve the story rather than illustrate transcript sentences. Art style is configurable per project through the visual bible, not fixed in code.

## Target Architecture

Two-step prompting:

1. **Scene-level intent (LLM, at storyboard time):** structured description — subject, action, location, characters present, emotion, time of day, shot type — derived from the story beat, not from transcript sentences ([storyboard-system](../domains/storyboard-system.md)).
2. **Prompt assembly (mostly code):** deterministic template merges scene intent with the **visual bible** (global style, palette, lighting, line style, aspect ratio, negative-prompt baseline) and **character bible** descriptors for each character present. An LLM may *polish* wording, but identity-bearing descriptors are copied verbatim from the bible so they stay stable ([consistency-strategy](consistency-strategy.md)).

Structure of a final prompt (model-dependent ordering, to be tuned per image model): `[style tokens] [subject + action] [character descriptors] [environment] [lighting/mood] [camera/framing]`. Negative prompt = global negatives + scene negatives (e.g. text, watermark, extra limbs).

Reference images and image-to-image inputs are passed through `reference_asset_ids` / future fields rather than described in text where possible ([image-consistency](../media/image-consistency.md)).

## Rules

- One idea per image; avoid prompts that require legible text in the image (subtitles are rendered by code).
- Framing leaves room for subtitles and camera motion: compose slightly wider than the final crop when the scene uses zoom/pan ([camera-motion](../media/camera-motion.md)).
- Record the exact final prompt, seed, model and bible versions on the asset metadata so the scene can be regenerated or varied ([asset-data-model](../data/asset-data-model.md)).

## Model role / input / structured output / validation / retry

LLM role: scene intent and optional prompt polish (cheap/mid tier). Input: one scene + bible entries. Output: `SceneSpec` fields validated by Pydantic; code checks that listed characters exist and prompt length fits the image model. Retry mechanism: [structured-output](structured-output.md).

## Cost and quality

Prompt building is cheap; the expense is image generation, so validate prompts before generating and avoid regenerating unchanged scenes ([ai-cost-strategy](ai-cost-strategy.md)). Quality is judged on the produced image ([image QA](../domains/quality-assurance.md)).

## Open questions

Prompt dialect per image model (tag-style vs natural language); who owns negative-prompt baselines; handling of historical accuracy (clothing, tools) as a prompt vs bible concern.

## Current vs future

Current: fields only. Future: prompt builder + [image-pipeline](../media/image-pipeline.md).
