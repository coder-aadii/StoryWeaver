# LLM Strategy

> Principles for choosing and using language models in StoryWeaver.

## Status

**Partially implemented** — provider seam and per-task model settings exist; strategy beyond configuration is **Planned**.

## Model/provider role

LLMs perform creative and analytical text tasks only: source analysis, topic/theme extraction, story-candidate generation, story architecture, script writing, scene/storyboard drafting, visual/character description, and (later) text-level QA. They do not do arithmetic on time, file operations, rendering decisions, or anything deterministic.

## Principles

1. **Local-first.** Default provider setting is `ollama` (`DEFAULT_LLM_PROVIDER`); the app must work with no cloud key. Rationale and trade-offs: [provider-selection](provider-selection.md#local-first-not-local-only), [ADR-002](../decisions/ADR-002-local-first.md).
2. **Provider independence.** Business logic calls `get_llm()` and the interface, never a vendor SDK ([ADR-003](../decisions/ADR-003-provider-abstraction.md)).
3. **No hard-coded model names.** Models come from settings: `DEFAULT_LLM_MODEL` and per-task `ANALYSIS_LLM_MODEL`, `STORY_LLM_MODEL`, `SCRIPT_LLM_MODEL`, `CLASSIFICATION_LLM_MODEL`. `Settings.model_for(task)` returns the task model or falls back to the default. No model is selected out of the box — calls raise `ProviderNotConfiguredError("no model selected")`.
4. **Structured over free text** whenever the output feeds other code ([structured-output](structured-output.md)).
5. **Right-size the model** per task ([model-routing](model-routing.md), [ai-cost-strategy](ai-cost-strategy.md)).
6. **Lazy loading.** No model is contacted or preloaded at API startup.

## Input context

Task-dependent; see [context-management](context-management.md). Planned inputs: transcript chunks, source metadata, retrieved facts ([rag-strategy](rag-strategy.md)), story architecture, character/visual bible entries.

## Prompt strategy

Prompts will be versioned files under `packages/prompts` (Planned); the recorded `prompt_version` column on `script_versions` already exists. See [prompting-strategy](prompting-strategy.md).

## Structured output, validation, retry

Implemented (mechanism, unit-tested with fakes and mocked HTTP): `generate_structured(prompt, PydanticModel, model=...)` appends the model's JSON Schema, extracts JSON from fences/prose, validates, and retries once with the error. After that it raises `ProviderResponseError`. Every failure inside `generate` — transport, HTTP status, timeout, empty or malformed reply — surfaces as a `ProviderError` subclass (previously KI-3, resolved in P0). Details: [structured-output](structured-output.md).

## Cost and quality considerations

Cost: [ai-cost-strategy](ai-cost-strategy.md). Quality: small local models struggle with long structured creative output; chunked, staged generation and validation are the mitigation (Target). Evaluation: [ai-quality-evaluation](ai-quality-evaluation.md).

## Current limitations

- No streaming, tool calling, token counting, rate limiting or response caching.
- Temperature/max_tokens are call parameters with defaults (0.7/2048 for `generate`, 0.2/4096 for `generate_structured`); no per-task tuning exists.
- Adapter behaviour against real services is unverified. Only the Ollama adapter has a mocked-HTTP test; the others have none.
- No live-service testing: all provider tests use mocked HTTP; the Google and OpenRouter adapters have had only one minimal manual connectivity check.

## Current vs future

Current: configuration + interface. Future: staged pipelines with routing, caching and evaluation. Provider choices are not permanent decisions.
