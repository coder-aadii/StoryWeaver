# ADR-004: AI decides content; deterministic code decides execution

> A hard boundary between creative decisions (AI) and mechanical media operations (code).

## Status

Accepted · 2026-10-01 · **Partially implemented** — the boundary is embodied in the schemas and `build_timeline`; most AI-side stages are Planned — not implemented.

## Context

LLMs are good at creative judgement and unreliable at exact arithmetic, timing, file handling and reproducibility. Media pipelines need the opposite. Mixing them produces unrepeatable, undebuggable videos.

## Decision

**AI decides content:**
source understanding · topic extraction · story-opportunity discovery (including "no suitable story") · story architecture · script · scene intent · visual descriptions · emotional beats · visual prompts · other creative decisions.

**Deterministic software decides execution:**
validation · schemas · persistence · IDs · asset relationships · timestamps · durations · subtitle timing · audio sync · timeline construction · rendering · encoding · retries · file management · reproducibility.

Rules that follow:

1. AI output enters the system only as validated structured data (`SceneSpec`, etc.), never as free text that code must interpret.
2. `SceneSpec.duration` is nullable and assigned by **code**, never by the LLM. Today a duration is either set explicitly or falls back to the deterministic estimate (`estimate_duration`, clamped 2–7 s). Deriving durations from **measured audio length** is **Planned — not implemented** (no code measures audio yet). The clamp truncates long narration, so the estimate must not be used for final output ([KI-16](../reference/status.md#known-issues-and-limitations)).
3. The renderer's only input is Timeline JSON; same input → same video.
4. An LLM is never asked to compute timestamps, mix audio, name files or encode video.
5. Retries and idempotency are properties of code paths, not of prompts.

## Alternatives considered

- Let an LLM emit full edit decision lists with timestamps: rejected — unverifiable and non-reproducible.
- Fully rule-based storytelling: rejected — cannot produce original narratives.

## Consequences

- Prompts and schemas are versioned; invalid output is rejected or retried, not patched silently ([structured-output](../ai/structured-output.md)).
- Pacing is a shared concern: AI supplies emotional beat/intent; code applies bounds ([timeline-system](../domains/timeline-system.md)).
- Testing splits cleanly: deterministic parts get exact tests; AI parts get evaluation ([testing-strategy](../testing/testing-strategy.md), [ai-quality-evaluation](../ai/ai-quality-evaluation.md)).

## Current implementation

Implemented: `SceneSpec`/`Timeline` schemas, `build_timeline`, unit tests for determinism and contiguity. Planned: everything on the AI side. See [vision](../product/vision.md), [media-pipeline](../architecture/media-pipeline.md).

## Revisit when

A pipeline stage needs a decision that straddles the boundary (e.g. pacing), or measured audio lengths are wired into the timeline.
