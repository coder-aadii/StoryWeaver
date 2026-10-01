# AI Cost Strategy

> How StoryWeaver aims for peak content quality at minimum monetary cost.

## Status

**Planned** (strategy) — only the enabling primitives are implemented: local-first defaults, provider abstraction, per-task model settings, duration/token logging.

## Objective

Maximise content quality, then minimise money spent to reach it. Cost is mostly **generation count × unit price**; the cheapest generation is the one you avoid.

## Principles

1. **Local-first inference.** Default provider `ollama`; the stack must run with zero recurring cost (reasoning in [provider-selection](provider-selection.md#local-first-not-local-only), [ADR-002](../decisions/ADR-002-local-first.md)). Hardware (Ryzen 5 5500U, 16 GB, no GPU) limits local model size and speed — expect small models and background processing.
2. **Optional cloud providers** (Google, OpenRouter, Grok, Claude-compatible adapters exist) used where quality demands. Concrete provider/model choices are configuration and **not permanent decisions** ([provider-selection](provider-selection.md)).
3. **Route by value.** Cheap models for routine work (classification, tagging, chunk notes, prompt polish); strong models for high-value creative decisions (story angles, architecture, script) ([model-routing](model-routing.md)). Planned.
4. **Extract once, reuse everywhere.** Facts/events/themes are stored and reused by all candidates and projects ([context-management](context-management.md)).
5. **Cache.** Key = hash(prompt version + inputs + model + params). Identical calls return stored results. Planned.
6. **Deduplicate.** Sources are unique per `(platform, external_id)` (implemented); duplicate chunks/near-duplicate sources should not be re-embedded or re-analysed.
7. **Avoid unnecessary image generation.** No AI video. One image may serve multiple shots with different camera moves ([camera-motion](../media/camera-motion.md)); reuse assets across scenes where narratively valid; regenerate only the failing scene; validate prompts before spending.
8. **Local rendering.** Remotion/FFmpeg run locally; no render cost.
9. **Budgets and visibility.** Per-project token/image budgets, recorded usage per call (`LLMResult` already carries tokens and duration; persistence Planned) ([monitoring](../operations/monitoring.md)).
10. **Fail cheap.** Validate cheap things first (schema, length, references) before expensive stages; cap retries.

## Stage gating: spend late, after human approval

> **Canonical description** of staged, cost-gated generation. Other documents link here rather than repeating it.

Bad: `source → 100 images → TTS → video → user rejects the story`.
Better (Target): `source → analysis → story candidates → user selects → script → storyboard → images → TTS → render`. Every expensive stage (images, voice, render) runs only after the cheaper upstream artifact is approved, and story-candidate selection is a **user approval gate** (an automatic pick may exist only as an opt-in shortcut). No gate state is persisted today ([approval and gate state](../domains/project-system.md#approval-and-gate-state-decision-pending); decision in [project-system](../domains/project-system.md)). Projects therefore need explicit approval points ([project-system](../domains/project-system.md), [workflow-overview](../workflows/workflow-overview.md)).

## Cacheable artifacts (Target — no caching layer exists today)

Source metadata, transcripts, normalized transcripts, chunks, embeddings, source analysis, topic extraction, story candidates, visual descriptions. Rows for metadata, transcripts and chunks already persist (tables exist); analysis/candidate/description persistence is Planned. Never pay twice to analyse the same source: key analysis by `(source_video_id, transcript version, prompt_version, model)`.

## Tracking and caching status (Planned — not implemented)

| Capability | Today |
| --- | --- |
| Response/analysis cache | None |
| Per-call usage record | Structured log only (`provider`, `model`, `duration`, `output_tokens`); note `output_tokens` is masked as `"***"` by the log redactor ([KI-2](../reference/status.md#known-issues-and-limitations)) and nothing is stored in the database |
| Budgets (per project tokens/images) | None |
| Prompt version on every artifact | `script_versions.prompt_version` only |

## Cost drivers (rough order, Target)

Image generation (if cloud) > script generation with strong model > story angle generation > embeddings (local ≈ free) > extraction. Measure before optimising.

## Model role / input / prompts / validation / retry

Retries multiply cost: one validation retry is built in; escalation is capped ([structured-output](structured-output.md)).

## Quality considerations

Do not cut spend at the story/script stage first — it determines everything downstream; evaluate cheaper models there with [ai-quality-evaluation](ai-quality-evaluation.md) before adopting.

## Current vs future

Current: no caching, budgets, or usage tables. Future: all of the above. Open: usage-record schema, currency conversion, user-facing budget UI.
