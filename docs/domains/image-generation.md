# Image Generation

> Producing illustrations for scenes through a provider-independent interface — illustrations with camera movement, **not** AI video.

## Status

**Partially implemented.** The `ImageGenerator` interface, a `MockImageGenerator` and a `ComfyUIProvider` **stub** exist. **No real image generation exists**: `ComfyUIProvider.generate` raises `ProviderNotConfiguredError` when `COMFYUI_BASE_URL` is unset and `ProviderError` ("ComfyUI workflow execution is not implemented yet") when it is set.

## Purpose

Create scene images cheaply and locally, one asset per scene/shot, regenerable individually.

## Problem being solved

AI video for every scene is slow and expensive. Still images plus deterministic camera motion, narration and music give a documentary feel at a fraction of the cost ([ADR-007](../decisions/ADR-007-media-rendering-strategy.md), [AI cost strategy](../ai/ai-cost-strategy.md)).

## Inputs

`ImageRequest`: `prompt`, `negative_prompt`, `width`, `height`, `seed`, `reference_asset_ids` (placeholder for the future list: reference images, character ids, style id, LoRA, ControlNet, init image).

## Outputs

`ImageResult(data, mime_type, metadata)`; target: stored as an `Asset` (type `image`, `status`, `storage_key`, `checksum`, `scene_id`) under `data/images/` ([asset data model](../data/asset-data-model.md)).

## Entities

`Asset`, `Scene`/`SceneVersion`. Separation: scene intent ≠ image prompt ≠ generated asset ≠ timeline shot — [storyboard system](storyboard-system.md).

## Workflow (Target Architecture)

Scene accepted → assemble prompt from scene intent + [visual bible](visual-system.md) + [character bible](character-system.md) → `ImageGenerator.generate` → store asset (`pending → generating → ready/failed`) → image QA ([quality assurance](quality-assurance.md)) → attach to timeline. Failure of one scene's image marks that asset `failed` with `error`; it never fails the project. Orchestration: [asset generation workflow](../workflows/asset-generation-workflow.md); pipeline: [image pipeline](../media/image-pipeline.md).

Expensive generation starts only **after story/script acceptance** ([story generation](story-generation.md)).

## Business rules

- Provider independence: ComfyUI is one implementation; cloud providers can be added behind the same interface ([provider architecture](../architecture/provider-architecture.md)).
- Per-scene regeneration is a core requirement: regenerating Scene 32 must not touch the script, other scenes or voice → assets are granular and versioned (asset versioning scheme: Decision pending).
- Avoid unnecessary generation: reuse one image across multiple shots via zoom/pan/crop/reframe before generating a new one.
- Seeds and the full request are recorded in asset metadata for reproducibility.

## AI responsibilities

Diffusion-model generation; prompt text by an LLM ([visual prompting](../ai/visual-prompting.md)); (future) vision-model QA.

## Deterministic responsibilities

Request assembly, resolution, seeds, file storage, checksums, status transitions, retries, reuse decisions, cache keys.

## Current implementation

- `get_image_generator()` returns ComfyUI provider if `COMFYUI_BASE_URL` is set, otherwise the mock — meaning that **setting the URL currently makes generation fail**, by design of the stub ([KI-18](../reference/status.md#known-issues-and-limitations)).
- `MockImageGenerator` returns a 64×36 solid PNG tagged `mock: true`; it is clearly fake and must never be shown as real output.
- `ComfyUIProvider.is_reachable()` pings `/system_stats` (surfaced by `GET /api/v1/health/providers`).
- No persistence of generated images, no workflow.

## Planned implementation

ComfyUI workflow submission, reference/character conditioning (image-to-image, LoRA, ControlNet where useful), alternate providers, image versioning, image QA.

## Edge cases

No GPU (Ryzen 5 5500U laptop; local generation may be very slow or infeasible — so the staged-cost design may in practice depend on a cloud image adapter; Decision pending); NSFW/safety filters; aspect-ratio mismatch with timeline; model files too large to load (never auto-download).

## Open questions

Local model choice; resolution policy (generate at 1344×768 vs upscale); batch vs on-demand generation.
