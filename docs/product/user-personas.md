# User Personas

> The people StoryWeaver is designed for, and the needs that drive design choices.

## Status

**Planned** (design input). No user research has been conducted; personas are working assumptions derived from the project brief. **Decision pending** on validating them with real users.

## P1 — The solo story creator (primary)

- **Who:** an individual producing story/documentary-style videos, technically comfortable (runs Docker/CLI), working on one laptop (Ryzen 5 5500U, 16 GB RAM, 1 TB disk, no GPU assumed).
- **Wants:** to turn knowledge from videos they already follow into original narrated, illustrated videos at near-zero cost.
- **Pain points:** watching/transcribing long videos by hand; paying for per-clip AI video; inconsistent characters; having to redo a whole video for one bad scene.
- **Drives:** local-first ([ADR-002](../decisions/ADR-002-local-first.md)), cost strategy ([ai-cost-strategy](../ai/ai-cost-strategy.md)), per-scene regeneration, lazy model loading.
- **Today:** can run the stack, browse empty library screens, create projects, preview a sample timeline. Cannot yet produce a real video.

## P2 — The knowledge curator

- **Who:** a creator who builds a large source library (many channels/playlists) and wants to find and reuse ideas.
- **Wants:** channel import with a count-then-choose step, searchable transcripts, collections ("History"), "have I already made a video on this?".
- **Drives:** [source-library](../domains/source-library.md), [channel-ingestion](../domains/channel-ingestion.md), [embeddings-and-vector-search](../data/embeddings-and-vector-search.md).
- **Today:** tables and a chunking helper exist; none of the flows do.

## P3 — The AI-pipeline tinkerer / contributor

- **Who:** a developer (or an AI coding agent) extending StoryWeaver: adding a provider, a domain, a Remotion composition.
- **Wants:** clear module boundaries, typed interfaces, tests, honest documentation of what exists.
- **Drives:** [adding-a-provider](../development/adding-a-provider.md), [adding-a-domain](../development/adding-a-domain.md), [adding-an-api-resource](../development/adding-an-api-resource.md), this documentation set.
- **Today:** the best-served persona.

## P4 — The reviewer / editor (within the same person)

- **Role:** the creator in review mode — approving story candidates, scripts and storyboards, flagging scenes to regenerate.
- **Wants:** a studio view of scenes with status, thumbnails and one-click regeneration.
- **Drives:** [studio](../frontend/studio.md), [storyboard-system](../domains/storyboard-system.md), [quality-assurance](../domains/quality-assurance.md).
- **Today:** Studio is a placeholder with a sample preview.

## Not in scope (for now)

Teams, clients, publishers and anonymous end-viewers: there is no auth, roles, sharing or publishing ([goals-and-non-goals](goals-and-non-goals.md)).

## Related

[user-flows](user-flows.md) · [use-cases](use-cases.md)
