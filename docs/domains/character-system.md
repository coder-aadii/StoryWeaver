# Character System (Character Bible)

> Keeping recurring characters recognisably the same across every scene of a video.

## Status

**Partially implemented.** `characters` and `locations` tables exist (per project, unique name, `description`, `attributes` JSONB). There is **no API endpoint, UI, generation or consistency logic**. `CharacterVersion`, reference-image linking and appearance modelling are **Deferred until required by the production workflow**.

## Purpose

Define each character once — identity, look, personality — and attach that identity to many scenes.

## Problem being solved

Image models drift: the same person gets different faces, clothes or ages across scenes. A structured character definition plus reference images is the basis for prompts and (later) conditioning.

## Inputs

Source-derived character descriptions, AI-proposed designs, user edits, reference images.

## Outputs

A character record used when building scene prompts ([visual prompting](../ai/visual-prompting.md)) and when QA checks scenes ([quality assurance](quality-assurance.md)).

## Entities

| Entity | State |
| --- | --- |
| `Character` | Implemented table: `project_id`, `name` (unique per project), `description`, `attributes` JSONB |
| `Location` | Implemented table, same shape |
| `CharacterVersion` | **Deferred** — not in schema |
| Appearance / ReferenceAsset | Planned; a reference image would be an `Asset` of type `reference` linked to a character (link mechanism **Decision pending**) |

Target `attributes` content (not enforced today): identity (name, role), age, appearance, hair, skin tone where relevant, clothing, body type, recurring accessories/props, personality cues, visual style notes, reference-asset ids. Scenes reference these canonical definitions instead of re-describing them. **Today the reference is only a convention:** `SceneSpec.characters` is a list of free strings; nothing in the schema ties a name to a `characters` row (unique on `(project_id, name)`), so resolving and validating names is workflow work ([storyboard system](storyboard-system.md#separate-concepts-intent--prompt--asset--shot)). The data-model direction for the Character Bible and Visual Bible is in the [story data model](../data/story-data-model.md).

## Workflow (Target Architecture)

Extract characters from the story → propose structured bible → user reviews/edits → (optional) generate reference images → lock a version → scenes reference characters by id/name → QA verifies appearance → edits create a new version, and affected scenes are flagged for regeneration ([asset workflow](../workflows/asset-generation-workflow.md)).

## Business rules (target)

- A character has one identity and a canonical text description fragment that is injected verbatim into every prompt that features them.
- Changing a character after images exist must not silently alter old images — hence versioning, which is why `CharacterVersion` will be needed.
- Characters are per-project today; cross-project reuse is **Decision pending**.

## AI responsibilities

Proposing characters/appearances from the story, writing prompt fragments, later vision-based consistency checking.

## Deterministic responsibilities

Name uniqueness, id resolution in scenes, prompt-fragment injection, reference management, version bookkeeping.

## Current implementation

DB tables only. Scenes reference characters as free strings in `SceneSpec.characters`; nothing resolves them.

## Planned implementation

Endpoints, UI, versioning, reference images, consistency conditioning (LoRA / image-to-image / IP-adapter-style methods — **Decision pending**, see [consistency strategy](../ai/consistency-strategy.md) and [image consistency](../media/image-consistency.md)).

## Edge cases

Characters aging across a story; groups/crowds; non-human or abstract subjects; historical figures; characters introduced mid-video.

## Open questions

Version granularity; reuse across projects; how strict consistency must be for stylised illustration vs realistic.
