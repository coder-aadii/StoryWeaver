# Image Consistency

> Technique and backend-capability reference for keeping characters and style consistent across generated images. The strategy and rationale live in [consistency-strategy](../ai/consistency-strategy.md); this page only compares techniques.

## Status

**Planned** — only the request field `ImageRequest.reference_asset_ids` and the `REFERENCE` asset type exist. Nothing below is implemented or decided.

## Techniques (ordered cheapest to heaviest)

Availability depends on the chosen image backend (ComfyUI workflows are the intended first one, currently a stub — [image-pipeline](image-pipeline.md)).

| Technique | What it gives | Cost / risk | Backend requirement |
| --- | --- | --- | --- |
| Verbatim descriptor text from the character/visual bible | Baseline identity and style | Free; weak on faces | Any |
| Fixed seed + fixed model/sampler per project | Reproducible re-renders | Free | Seed control |
| Style tokens / fixed checkpoint | Style uniformity | Free | Checkpoint pinning |
| Reference image conditioning (image-to-image, IP-Adapter-style) | Stronger identity | Needs a supporting workflow; risk of copying pose | Reference input |
| LoRA per character/style | Strongest identity | Training time and storage; **Decision pending** | LoRA loading |
| ControlNet (pose/depth/edges) | Composition control where needed | Complexity; use selectively | ControlNet nodes |
| Reusing the same image for several shots | Perfect continuity | Limited variety | None (camera-motion only; [camera-motion](camera-motion.md)) |

## Record to keep per generated asset (Target)

Prompt, seed, model, workflow, reference ids and bible versions, stored with the asset ([asset-data-model](../data/asset-data-model.md)); the process that uses them is described once, in [consistency-strategy](../ai/consistency-strategy.md#target-architecture--layers-of-control).

## Failure modes specific to techniques

Reference over-conditioning (copying the pose); style change when a model is swapped mid-project (pin the model per project); intended vs accidental costume changes (needs `CharacterVersion`, **deferred**).

## Related

[image-pipeline](image-pipeline.md) · [visual-prompting](../ai/visual-prompting.md) · [visual-system](../domains/visual-system.md)
