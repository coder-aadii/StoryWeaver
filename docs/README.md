# StoryWeaver Documentation

> **From source to story to video.** The long-term technical and product knowledge base for StoryWeaver.

## Status

Implemented (documentation). The documentation set is complete for the foundation; see [implementation status](reference/status.md) for what the *software* does today.

## What StoryWeaver is

A local-first, AI-assisted story-to-video production engine. It is **not** a generic AI video generator: it takes a source (a YouTube video, a transcript, …), understands it, finds the story in it, writes an **original** script, plans scenes, generates illustrations and narration, and assembles a deterministic video with camera motion, subtitles and audio. Principle: **AI decides content; deterministic code decides timing, assets and rendering.** Goal: maximum content quality at minimum monetary cost.

Start with [product overview](product/product-overview.md) and [vision](product/vision.md).

## Current implementation status — read this first

StoryWeaver today is a **foundation**: API, database schema, provider interfaces, a web shell, a timeline builder and a basic Remotion composition. The product pipeline itself (ingestion workflows, story/script/storyboard generation, real image and voice generation, QA) is **not implemented**.

→ **[Implementation status matrix](reference/status.md)** is canonical, and its [known issues](reference/status.md#known-issues-and-limitations) section lists code defects the docs describe but do not fix. Every document carries a `Status` of *Implemented*, *Partially implemented*, *Planned* or *Future*; target designs are labelled *Target Architecture*.

## Documentation map

| Section | What it answers |
| --- | --- |
| [product/](product/product-overview.md) | Why, for whom, requirements, roadmap, terminology, source-usage policy |
| [architecture/](architecture/overview.md) | How the system is built (and the target) |
| [domains/](domains/source-library.md) | One document per business domain: inputs, outputs, rules, AI vs deterministic |
| [data/](data/data-model.md) | Tables, relationships, storage layout, vectors, lifecycle |
| [ai/](ai/ai-overview.md) | LLM strategy, routing, prompting, structured output, RAG, cost, evaluation |
| [media/](media/media-overview.md) | Images, voice, subtitles, timeline spec, camera motion, Remotion, FFmpeg |
| [workflows/](workflows/workflow-overview.md) | Long-running job designs, retries, recovery |
| [api/](api/README.md) | REST conventions, health, per-resource reference |
| [frontend/](frontend/README.md) | Next.js app, state, data fetching, Studio |
| [development/](development/setup.md) | Setup, workflow, standards, how-to guides, [AI agent guide](development/ai-agent-guide.md) |
| [operations/](operations/local-environment.md) | Environment, Docker, configuration, logging, backups, deployment |
| [testing/](testing/testing-strategy.md) | Strategy and gates |
| [security/](security/security-overview.md) | Threat model, secrets, validation, file safety |
| [decisions/](decisions/README.md) | Architecture Decision Records |
| [reference/](reference/status.md) | [Status](reference/status.md), [glossary](reference/glossary.md), [commands](reference/commands.md), [environment](reference/environment-reference.md), [schemas](reference/schemas.md), [changelog](reference/changelog.md) |

## Entry points by role

- **Architecture:** [overview](architecture/overview.md) → [system architecture](architecture/system-architecture.md) → [data flow](architecture/data-flow.md) → [domain architecture](architecture/domain-architecture.md).
- **Product:** [vision](product/vision.md) → [requirements](product/requirements.md) → [feature roadmap](product/feature-roadmap.md) → [terminology](product/terminology.md).
- **Development:** [setup](development/setup.md) → [development workflow](development/development-workflow.md) → [repository structure](development/repository-structure.md) → [testing](development/testing.md).
- **AI / media:** [AI overview](ai/ai-overview.md) → [story generation pipeline](ai/story-generation-pipeline.md) → [media overview](media/media-overview.md) → [timeline specification](media/timeline-specification.md).
- **Coding agents:** [AI agent guide](development/ai-agent-guide.md), then [status](reference/status.md).
- **Decisions:** [ADR index](decisions/README.md).

## The pipeline at a glance

See the diagram in [vision](product/vision.md). Stages: Source → Research → Idea → Story architecture → Script → Storyboard → Visual/Character bible → Images → Voice/Audio → Timeline → Render → QA → Final video. Implemented today: a slice of Source (abstractions), the Timeline builder, and a basic Render of a sample timeline.

## How to update the documentation

1. Change code and docs in the same change. At minimum update [status](reference/status.md) when something becomes (or stops being) real.
2. Put canonical information in **one** document and link to it from others; don't duplicate.
3. Keep the header contract: `# Title`, `> purpose`, `## Status`. Use *Target Architecture* for designs, and "Planned — not implemented", "Decision pending", "Deferred until required by the production workflow" for unbuilt or undecided things. Never describe planned behavior in the present tense as if it exists.
4. Verify current-state claims against the code (routes, models, settings, tests) before writing them.
5. Significant architectural decisions get an ADR ([template and index](decisions/README.md)).
6. Use relative links and Mermaid diagrams where they clarify; check links, anchors and the header contract before requesting a commit (no automated checker exists; see the manual procedure in [quality gates](testing/quality-gates.md)).
7. Add notable changes to the [changelog](reference/changelog.md).
