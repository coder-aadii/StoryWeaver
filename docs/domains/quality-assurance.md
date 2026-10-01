# Quality Assurance

> Automatically checking the produced video — and each scene — before it is called finished.

## Status

**Planned — not implemented.** `apps/api/app/quality/` is a docstring-only placeholder; `ProjectStatus.QA` exists as a state. Repository-level tests (pytest/Vitest/Playwright) test the *software*, not generated videos — see [testing strategy](../testing/testing-strategy.md).

## Purpose

Catch defects (technical and creative) early, per scene, and drive targeted regeneration instead of whole-project rebuilds.

## Problem being solved

AI outputs are unreliable: wrong characters, artefacts, mismatched narration, clipped audio. Manual review of every scene doesn't scale.

## Inputs

Timeline, assets, scene specs, bibles, rendered MP4.

## Outputs

A structured QA result per scene/asset and per render (check name, verdict, evidence, severity), driving regeneration suggestions.

## Entities

No QA entity exists (result storage Decision pending: JSONB on `Asset`/`Render` vs dedicated table). `Asset.status`/`error` and `Scene.status`/`error` already carry failure state.

## Planned checks (Target Architecture)

| Category | Checks | Method |
| --- | --- | --- |
| Completeness | missing images/audio/subtitles for any scene | deterministic |
| Technical | render failure, wrong resolution/fps, black frames, silence gaps, audio clipping, loudness out of range, duration vs timeline mismatch | deterministic (FFmpeg analysis) |
| Subtitle/narration | text mismatch, cues too long, desync | deterministic + alignment |
| Visual content | wrong character, wrong object, incorrect action, style inconsistency, artefacts (extra limbs, garbled text) | vision-model judgement (AI) — thresholds Decision pending |
| Story | beat coverage, pacing outliers | heuristics + optional LLM |

Deterministic checks come first (cheap, reliable); AI visual checks run only on assets that pass them ([AI cost strategy](../ai/ai-cost-strategy.md)).

## Workflow

Run after asset generation (per-scene) and after render (whole-video) — [QA workflow](../workflows/qa-workflow.md). Failing scenes are marked and can be **regenerated individually**: new asset version for that scene only; re-run QA for it; rebuild timeline and re-render. The rest of the project is untouched ([retry and recovery](../workflows/retry-and-recovery.md)).

## Business rules

- QA never silently edits content; it reports and proposes.
- Regeneration attempts are bounded (count Decision pending) to avoid infinite loops/cost.
- Every failure is persisted with enough context to retry.

## AI responsibilities

Visual/semantic judgement of images against the scene spec and bibles ([AI quality evaluation](../ai/ai-quality-evaluation.md)).

## Deterministic responsibilities

File/stream checks, durations, levels, subtitle timing, aggregation, retry bookkeeping.

## Current implementation

None.

## Planned implementation

Roadmap phase 6 ([feature roadmap](../product/feature-roadmap.md)); architecture in [quality architecture](../architecture/quality-architecture.md).

## Edge cases

False positives on stylised art; subjective quality; QA model cost on long videos (sample frames); non-determinism of AI judges.

## Open questions

Which vision model; acceptance thresholds; human-approval gates.
