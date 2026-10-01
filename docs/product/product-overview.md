# Product Overview

> What StoryWeaver is, who it is for, and how much of it exists today.

## Status

**Partially implemented.** The foundation (data model, API, provider interfaces, a Remotion composition, a UI shell) exists. The production capabilities that make up the product (ingestion workflows, story generation, image/voice generation, full video production, QA) are **Planned — not implemented**. The canonical per-subsystem matrix is [reference/status.md](../reference/status.md).

## What StoryWeaver is

StoryWeaver is a **local-first, AI-assisted story-to-video production engine**. Tagline: *From source to story to video.*

It takes source material (a YouTube video, channel, playlist, transcript, local media, later documents/web pages), builds a reusable knowledge library from it, and — on request — turns ideas found in that library into **original, story-driven videos** of roughly 10–15 minutes. Visuals are **generated illustrations with camera movement** (zoom, pan), transitions, narration, subtitles, music and sound effects — not per-scene AI video clips. The aim is something that feels like an edited story/documentary, not a static slideshow.

It is explicitly **not** a paraphraser or a transcript-to-slideshow converter. See [story-generation](../domains/story-generation.md).

## Core idea in one picture

```text
Source → understanding → idea → story architecture → original script → storyboard
       → visual/character bible → illustrations → narration/audio → timeline → render → QA → MP4
```

The full diagram and stage-by-stage status are in [vision.md](vision.md). Defects and gaps found in the current code are listed in [status — known issues](../reference/status.md#known-issues-and-limitations).

## Guiding principles

1. **AI decides content; code decides timing, assets and rendering** ([ADR-004](../decisions/ADR-004-ai-vs-deterministic-responsibilities.md)).
2. **Local-first** with minimal mandatory recurring cost ([ADR-002](../decisions/ADR-002-local-first.md)).
3. **Provider independence** — swap Ollama / Google / OpenRouter / Grok / Claude-compatible without rewriting business logic ([ADR-003](../decisions/ADR-003-provider-abstraction.md)).
4. **Structured data** over free text for every important artefact ([data model](../data/data-model.md)).
5. **Granular regeneration** — any scene or asset can be regenerated without rebuilding the project.
6. **Version everything important** — scripts, scene specs, prompts.
7. **Do not over-engineer** — a modular monolith, not microservices ([ADR-006](../decisions/ADR-006-modular-monolith.md)).

## Who it is for

Primarily a single creator running on a modest local machine (the reference development machine is a Ryzen 5 5500U laptop, 16 GB RAM, no GPU assumed). See [user-personas.md](user-personas.md).

## What exists today (summary)

| Capability | State |
| --- | --- |
| API with 10 CRUD resource groups + health endpoints | Implemented ([api](../api/README.md)) |
| PostgreSQL + pgvector schema (17 tables) and Alembic migration | Implemented ([database-schema](../data/database-schema.md)) |
| Provider interfaces (LLM, embeddings, image, voice, transcription, source extraction) | Interfaces + thin adapters. Only Ollama's chat request has a (mocked-HTTP) test (the embedding adapters have none); the Google, OpenRouter, Grok and Claude-compatible adapters are untested, and none has run against a real service |
| Deterministic timeline builder; Remotion `Basic` composition; sample MP4 render | Implemented; render uses Remotion's bundled encoder, system FFmpeg is not required ([timeline-specification](../media/timeline-specification.md)) |
| Next.js shell: dashboard, sources, topics, collections, projects, studio (placeholder), settings | Implemented ([frontend](../frontend/README.md)) |
| Channel import, transcript pipeline, research/RAG, story + script + storyboard generation, real image/voice generation, QA, durable workflows, auth | **Planned — not implemented** |

## Where to go next

- Vision and pipeline: [vision.md](vision.md) · scope: [goals-and-non-goals.md](goals-and-non-goals.md)
- What must be true: [requirements.md](requirements.md) · what is next: [feature-roadmap.md](feature-roadmap.md)
- How it is built: [architecture overview](../architecture/overview.md)
- Vocabulary: [terminology.md](terminology.md)
