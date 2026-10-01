# Architecture Decision Records

> Index of significant decisions, why they were made, and how to add or change one.

## Status

**Implemented** (process and records). Individual ADRs state their own status; all current ADRs are *accepted*.

| ADR | Decision | Status |
| --- | --- | --- |
| [ADR-001](ADR-001-stack.md) | Technology stack and module boundaries | Accepted · Implemented (items 2, 3, 6, 7, 10 superseded in part by ADR-004/005/006/007) |
| [ADR-002](ADR-002-local-first.md) | Local-first operation, not local-only | Accepted · Partially implemented |
| [ADR-003](ADR-003-provider-abstraction.md) | Provider-independent AI interfaces | Accepted · Partially implemented |
| [ADR-004](ADR-004-ai-vs-deterministic-responsibilities.md) | AI decides content; code decides execution | Accepted · Partially implemented |
| [ADR-005](ADR-005-postgres-pgvector.md) | PostgreSQL + pgvector as the single data store | Accepted · Implemented (embedding generation Planned) |
| [ADR-006](ADR-006-modular-monolith.md) | Modular monolith, not microservices | Accepted · Implemented (structure) |
| [ADR-007](ADR-007-media-rendering-strategy.md) | Illustrations + camera motion rendered deterministically (Remotion; FFmpeg role pending) | Accepted · Partially implemented |
| [ADR-008](ADR-008-storage-strategy.md) | Filesystem storage behind an abstraction | Accepted · Partially implemented |
| [ADR-009](ADR-009-render-asset-resolution.md) | Assets reach the renderer as project-relative keys resolved via a per-render Remotion public dir | Accepted · Partially implemented |

## How ADRs are used

- An ADR records **why**, with alternatives and consequences. Current behaviour belongs in architecture docs; the ADR links to them.
- ADRs are append-only in spirit: to change a decision, add a new ADR and mark the old one *Superseded by ADR-00X* rather than rewriting history.
- Template (every ADR follows it): **Status** (accepted/superseded · date · implementation state) · **Context** · **Decision** · **Alternatives considered** · **Consequences** · **Revisit when**. Implementation state must agree with [status.md](../reference/status.md).
- Keep ADRs short; put detail in the linked docs ([architecture overview](../architecture/overview.md), [status](../reference/status.md)).

## Decisions still pending

Tracked where they arise, not yet ADRs: per-task provider routing ([model-routing](../ai/model-routing.md)); embedding model and dimension policy ([embeddings](../ai/embeddings.md)); TTS engine; ComfyUI workflow design ([image-pipeline](../media/image-pipeline.md)); paraphrase-rejection threshold ([content policy](../product/content-policy-and-source-usage.md)); when to adopt Temporal ([workflow-architecture](../architecture/workflow-architecture.md)); FFmpeg's role beyond Remotion's bundled encoder ([ffmpeg](../media/ffmpeg.md)); raw-vs-cleaned transcript storage ([transcript-pipeline](../domains/transcript-pipeline.md)); where approval-gate state and story candidates/analysis are stored ([project-system](../domains/project-system.md), [story-data-model](../data/story-data-model.md)); the artifact dependency/invalidation model ([workflow-overview](../workflows/workflow-overview.md)).
