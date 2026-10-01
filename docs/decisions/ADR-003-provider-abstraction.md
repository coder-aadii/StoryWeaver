# ADR-003: Provider-independent AI interfaces

> Business logic depends on small interfaces, never on a specific AI provider.

## Status

Accepted · 2026-10-01 · **Partially implemented** — interfaces and thin adapters exist; test coverage is thin: only Ollama's chat request has a mocked-HTTP test (embedding adapters and the other LLM adapters have none), `generate_structured` is tested through a fake provider, and the Google, OpenRouter, Grok and Claude-compatible adapters have no tests. No adapter has been exercised against a real service.

## Context

Models, prices and availability change quickly. The owner has access to Ollama, Google AI, Grok, OpenRouter and a Claude-compatible endpoint today; that list is a configuration fact, **not a permanent decision**.

## Decision

- LLMs: `LLMProvider.generate()` and `generate_structured()` (JSON validated against a Pydantic schema, one retry with the validation error). Providers implement only `_complete()`.
- Embeddings: `EmbeddingProvider.embed()`.
- Images: `ImageGenerator` (ComfyUI stub, mock). Voice: `VoiceProvider` (unconfigured default). Transcription: `Transcriber` (faster-whisper, lazy optional). Source extraction: `SourceExtractor`.
- A lazy registry (`intelligence/registry.py`) creates providers on use; unknown names raise a clear error; unconfigured providers raise `ProviderNotConfiguredError` only when called.
- OpenRouter and Grok share one OpenAI-compatible adapter; Google and Claude-compatible have their own.
- Model names are configuration (`DEFAULT_LLM_MODEL`, per-task overrides), never constants in business logic.

## Alternatives considered

- Adopt a third-party multi-provider SDK: adds a dependency and its abstractions; **Decision pending** if maintenance burden grows.
- Call provider SDKs directly where needed: rejected — couples domain code to vendors.

## Consequences

- Swapping providers is a config change; adding one is a small class ([adding-a-provider](../development/adding-a-provider.md)).
- The lowest-common-denominator interface hides provider-specific features (tool use, JSON mode, streaming). Add them to the interface only when a pipeline stage needs them.
- Per-task *provider* routing (not just per-task model) is **Decision pending** ([model-routing](../ai/model-routing.md)).
- Health endpoint reports configured/reachable without exposing keys ([provider-endpoints](../api/provider-endpoints.md)).
- Failure isolation: every failure inside a provider call surfaces as a `ProviderError` subclass (`ProviderTimeoutError`, `ProviderResponseError`), verified by a shared mocked-HTTP contract suite (previously KI-3, resolved in P0). No workflow persists failure state or retries yet.
- Provider calls are intended to be observable, timeout-controlled (120 s today), validated, retryable and replaceable; a provider failure must not corrupt project state.

Architecture detail: [provider-architecture](../architecture/provider-architecture.md), [ai-architecture](../architecture/ai-architecture.md).

## Revisit when

Per-task provider routing is needed (see [model-routing](../ai/model-routing.md)), or maintaining the adapters costs more than adopting a multi-provider SDK.
