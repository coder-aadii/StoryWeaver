# AI Quality Evaluation

> How generated content quality will be measured and regressions caught.

## Status

**Planned** — no evaluation harness or fixtures exist. Related: [ai-evaluation (testing)](../testing/ai-evaluation.md).

## Problem

Model/prompt changes silently alter output quality. Creative output has no single correct answer, so quality must be assessed through layered checks.

## Target Architecture

| Layer | What | How | Cost |
| --- | --- | --- | --- |
| 1. Structural | Valid schema, required beats present, length within range | Code | free |
| 2. Referential | Characters/locations exist; claims cite source evidence; no unknown ids | Code | free |
| 3. Grounding | Facts in script supported by extracted facts | Code + cheap LLM check | low |
| 4. Originality | Low n-gram/embedding overlap with transcript | Code (embeddings) | low |
| 4b. Similarity to prior work | Overlap with previous projects' scripts and previously used story ideas | Code (embeddings + pgvector); **requires used-idea / project-script embeddings that are not stored today** ([KI-22](../reference/status.md#known-issues-and-limitations), direction in [embeddings-and-vector-search](../data/embeddings-and-vector-search.md)) | low |
| 5. Narrative quality | Hook strength, tension, escalation, resolution, pacing | LLM-as-judge with rubric, calibrated by human ratings | medium |
| 6. Human review | Final selection and edits | Person | — |

Layers 4 and 4b are engineering signals for source-use discipline and avoiding repetition; they make **no legal or copyright determination**. Visual and audio evaluation is covered in [quality-architecture](../architecture/quality-architecture.md) and [quality-assurance](../domains/quality-assurance.md).

## Evaluation sets (Planned)

Small fixed corpus of 5–10 transcripts of varied length/genre, stored as fixtures; each prompt/model change runs the pipeline and records metrics side by side. Keep outputs versioned for comparison. LLM judges must use a different model than the generator where possible, and are never the sole signal.

## Metrics to record

Validity rate on first pass; retries per call; latency; tokens; originality overlap; grounding coverage; rubric scores; human preference. Tie them to `prompt_version`, `provider`, `model` ([prompting-strategy](prompting-strategy.md)).

## Model role / input / structured output / validation / retry

Judge calls use [structured-output](structured-output.md) with a rubric schema (scores + justification). Judge disagreement or low confidence escalates to human review.

## Cost considerations

Run full evaluation only on prompt/model changes, not per project. Use cheap checks (layers 1–4) in CI-like runs ([quality-gates](../testing/quality-gates.md)); LLM-judge runs are opt-in.

## Current vs future

Current: unit tests for the structured-output mechanism only. Future: fixtures, harness, dashboards. Open: rubric definition, human-rating workflow, acceptable thresholds — Decision pending.
