# Goals and Non-Goals

> The boundaries of the product: what we are trying to achieve and what we deliberately are not.

## Status

**Planned** (a statement of intent). The foundation honours these boundaries; most goals are not yet delivered — see [reference/status.md](../reference/status.md).

## Goals

| # | Goal | Why | Where it shows up |
| --- | --- | --- | --- |
| G1 | Local-first operation with no mandatory recurring cost | Creator runs on a laptop; cloud optional | [ADR-002](../decisions/ADR-002-local-first.md) |
| G2 | Provider independence for LLM, embeddings, image, voice, transcription | Providers/prices change | [ADR-003](../decisions/ADR-003-provider-abstraction.md) |
| G3 | Original stories, not paraphrases | Quality and originality | [story-generation](../domains/story-generation.md) |
| G4 | Deterministic media pipeline | Reproducible, debuggable output | [ADR-004](../decisions/ADR-004-ai-vs-deterministic-responsibilities.md) |
| G5 | Illustration + camera motion instead of AI video | Cost and hardware | [ADR-007](../decisions/ADR-007-media-rendering-strategy.md) |
| G6 | Structured, versioned data for every important artefact | Regeneration, audit | [data-model](../data/data-model.md) |
| G7 | Per-scene/per-asset regeneration | Avoid rebuilding projects | [retry-and-recovery](../workflows/retry-and-recovery.md) |
| G8 | Reusable source knowledge (search, collections, reuse across projects) | One source → many projects | [source-library](../domains/source-library.md) |
| G9 | Runs on ~16 GB RAM, no GPU required to boot | Reference dev machine | [scalability](../architecture/scalability.md) |
| G10 | Maximum content quality at minimum monetary cost (spend more where creative impact is high, less on routine tasks) | Core economics | [ai-cost-strategy](../ai/ai-cost-strategy.md) |
| G11 | Story-first output: the system decides whether and what story a source yields, including "none" | Not a generic video generator | [vision](vision.md), [story-generation](../domains/story-generation.md) |
| G12 | Provider failure isolation: a failed provider call or a failed scene never corrupts project state; calls are timeout-controlled, validated, retryable and replaceable | Reliability of long pipelines | [retry-and-recovery](../workflows/retry-and-recovery.md), [provider-architecture](../architecture/provider-architecture.md) |

## Non-goals (current phase and by design)

- **Not a generic video editor.** The Studio is a placeholder; a full timeline editor is **Future** ([studio](../frontend/studio.md)).
- **Not AI video generation per scene.** Expensive clip generation is out of scope by design.
- **Not a media downloader.** Building the source library does **not** require downloading video files; storing metadata, transcripts, chunks and embeddings is the default. Media download is an optional future capability only when a workflow genuinely needs it ([source-library](../domains/source-library.md)).
- **Not a paraphraser, summariser or synonym-swapper** of source transcripts; **not** a transcript-to-slideshow tool (no one-image-per-paragraph, no mechanical scene splitting, no fixed time-slice videos).
- **Not a generic AI video generator.** See [vision](vision.md). AI-agent contributors: read [ai-agent-guide](../development/ai-agent-guide.md).
- **Not microservices.** One FastAPI app with modular packages ([ADR-006](../decisions/ADR-006-modular-monolith.md)).
- **Not multi-user / SaaS** yet: no authentication, billing or tenancy ([authentication](../api/authentication.md), [security-overview](../security/security-overview.md)).
- **Not a publisher.** YouTube publishing/upload is not planned in the current phase.
- **Not GPU-dependent.** GPU-accelerated providers may be used when present but are never required to boot.
- **Not tied to any provider.** Current provider list is a configuration fact, not a permanent decision.
- **Not a Kubernetes/AWS deployment target** at this stage ([deployment](../operations/deployment.md)).

## Success criteria for the foundation phase (met)

Backend boots without optional providers; migrations apply; health endpoints work; web shell loads and talks to the API; a Remotion composition renders a sample timeline to MP4; tests and lint pass. Caveat: the Docker Compose path has **never been run** on the development machine (Docker was not installed); the Docker-free Postgres helper was. Known defects found afterwards are tracked in [status — known issues](../reference/status.md#known-issues-and-limitations). Evidence: [testing-strategy](../testing/testing-strategy.md), [quality-gates](../testing/quality-gates.md).

## Success criteria for later phases (Planned)

Defined per roadmap phase in [feature-roadmap.md](feature-roadmap.md). Measurable output-quality criteria are **Decision pending** (see [ai-quality-evaluation](../ai/ai-quality-evaluation.md)).
