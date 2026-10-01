# ADR-002: Local-first, not local-only

> StoryWeaver must run end to end on the creator's machine at minimal recurring cost, while allowing cloud services where they add real value.

## Status

Accepted · 2026-10-01 · **Partially implemented** (boot and configuration are local-first; local AI/media engines are mostly not yet wired).

## Context

The reference machine is a Ryzen 5 5500U, 16 GB RAM, no GPU assumed. Creative quality benefits from strong models, which are often cloud-hosted and paid. The product goal is **maximum content quality for minimum monetary cost** — not minimum cost at any cost.

## Decision

1. The core application (API, database, UI, rendering) runs locally with **no mandatory cloud service and no mandatory GPU**.
2. Every AI/media capability sits behind an interface ([ADR-003](ADR-003-provider-abstraction.md)); local engines (Ollama, ComfyUI, local TTS, faster-whisper) are preferred defaults for routine work.
3. Cloud providers are **optional**: used where a stronger model clearly improves an important creative decision (e.g. story architecture), or when local hardware cannot do the job.
4. Nothing heavy loads at import/startup (lazy engine and provider registry); optional providers being unset must never fail boot.
5. Rendering, timeline construction and storage are always local and deterministic.

## Alternatives considered

- **Cloud-only SaaS stack:** simplest, but recurring cost and vendor lock-in; rejected.
- **Local-only, no cloud ever:** caps quality on creative steps; rejected as a hard rule — local-first, not local-only.

## Consequences

- Configuration exposes per-task model names and keeps keys in server-side `.env` ([configuration](../operations/configuration.md)).
- Docker is optional (a Docker-free Postgres helper exists); Temporal and MinIO are opt-in compose profiles and unused ([docker](../operations/docker.md)).
- Local AI quality/latency on CPU-only hardware is **unmeasured**; expect some tasks to need cloud or smaller models ([scalability](../architecture/scalability.md), [ai-cost-strategy](../ai/ai-cost-strategy.md)).
- Local vs cloud flow diagram: [ai-architecture](../architecture/ai-architecture.md).

## Current implementation

Boot with no providers: Implemented and tested. Ollama LLM/embedding adapter: Implemented; its HTTP shape is tested against a mock only (never against a real Ollama). Image/voice/transcription local engines: interfaces, stub or optional extras ([status](../reference/status.md)).

## Revisit when

A GPU becomes available, or local models prove inadequate for a pipeline stage.
