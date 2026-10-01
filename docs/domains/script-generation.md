# Script Generation

> Producing a versioned, validated narration script (10–15 minutes by default) from a chosen story architecture.

## Status

**Planned — not implemented.** Tables `scripts` and `script_versions` and basic CRUD for `scripts` exist; script *versions* have no API endpoint and no generation code exists.

## Purpose

Write the spoken narrative that drives scenes, voice, subtitles and timing.

## Problem being solved

Scripts must be original, paced for narration, structurally sound and traceable — and must be regenerable without losing earlier drafts.

## Inputs

Story architecture ([story generation](story-generation.md)), target duration, tone/voice style, supporting facts.

## Outputs

`ScriptVersion` with `content` (JSON), plus `prompt_version`, `provider`, `model`.

## Entities

`Script` (`project_id`, `title`) → `ScriptVersion` (`version`, `content` JSONB, `prompt_version`, `provider`, `model`; unique `(script_id, version)`). The shape of `content` is **Decision pending**; target: ordered beats, each with narration paragraphs and source-fact references.

## Workflow (Target Architecture)

Draft by beat → assemble → validate → store as new version → (optional) revise with critique → new version. Revisions never mutate a prior version.

## Business rules

- Length target ~10–15 minutes ≈ 1,500–2,250 words at the code's 2.5 words/second narration estimate (`WORDS_PER_SECOND` in `app/video/timeline.py`); real length is measured from synthesized audio later, not trusted from the LLM ([timeline system](timeline-system.md)). This word-count arithmetic applies to the **whole script**: the per-scene `estimate_duration` clamps each scene to 2–7 s, so summing per-scene estimates under-counts any scene with more than ~17 words and must not be used to check script length ([KI-16](../reference/status.md#known-issues-and-limitations)).
- Narration is written to be *heard*: short sentences, no references to on-screen text unless intended.
- Validation checks (planned): structure complete, length within tolerance, no invented source quotes, originality threshold, forbidden content.

## AI responsibilities

Writing, revision, self-critique. Prompting: [prompting strategy](../ai/prompting-strategy.md), [structured output](../ai/structured-output.md).

## Deterministic responsibilities

Word/duration estimation, schema validation, versioning, similarity measurement, persistence.

## Current implementation

Tables + `/api/v1/scripts` (create with project & title, list, get, patch title, delete). Nothing creates `ScriptVersion` rows.

## Planned implementation

Version endpoints, generation workflow ([story generation workflow](../workflows/story-generation-workflow.md)), diff/compare UI in Studio.

## Edge cases

LLM returns too short/long output; truncation at token limit (chunk by beat); revisions invalidating storyboard (scenes reference script version — link field Decision pending).

## Open questions

Script `content` schema; language/locale support; multi-voice (dialogue) scripts.
