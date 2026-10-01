# Structured Output

> How LLM output becomes validated, typed data.

## Status

**Implemented (mechanism, unit-tested with fakes)** — consistent with *Partially implemented* in [status](../reference/status.md) for the LLM layer. It has only been exercised through a fake provider and one mocked Ollama response, never against a real model, and no pipeline stage uses it yet.

## Current implementation

`LLMProvider.generate_structured(prompt, schema, *, system, model, temperature=0.2, max_tokens=4096, retries=1)` in [`providers/base.py`](../../apps/api/app/intelligence/providers/base.py):

1. Appends `"Respond with ONLY a JSON object matching this JSON Schema: …"` using `schema.model_json_schema()`.
2. Calls `generate`.
3. `extract_json` strips Markdown code fences and surrounding prose, taking the span from the first `{` to the last `}`. Arrays at top level are not supported — wrap them in an object.
4. `schema.model_validate_json` validates.
5. On `ValidationError`/`ValueError`, retries up to `retries` more times, appending "Fix this error: <first 500 chars>" to the prompt. After exhaustion raises `ProviderError`.
6. **Unusable replies:** an empty reply, a blocked reply (e.g. Google safety block, or a reasoning model that spent its whole token budget) or a malformed one raises `ProviderResponseError` inside `generate`; `generate_structured` treats it like invalid output — it retries once and then raises `ProviderResponseError` (previously KI-3, resolved in P0). Transport and HTTP-status failures are not retried here: they propagate as `ProviderError`/`ProviderTimeoutError` (backoff is **Planned — not implemented**).

Tests ([`test_units.py`](../../apps/api/tests/test_units.py)): retry-then-success and give-up (both with a fake `LLMProvider` subclass), and JSON extraction from prose. The only HTTP-level adapter test is for Ollama; Google, OpenRouter, Grok and Claude-compatible adapters have no tests.

Provider-native JSON modes (Ollama `format`, OpenAI `response_format`, Google response schema) are **not** used — Planned; they would raise first-pass validity on small models.

## Contracts that exist

[`schemas/scene.py`](../../apps/api/app/schemas/scene.py): `SceneSpec`, `CameraSpec`, `Timeline`, `TimelineScene`. [`schemas/source.py`](../../apps/api/app/schemas/source.py): `NormalizedSource`, `TranscriptSegment`. Exported as JSON Schema in `packages/schemas` ([schemas reference](../reference/schemas.md)). Story, script and analysis schemas: Planned — not implemented.

## Target Architecture

- One Pydantic model per stage output (e.g. `SourceAnalysis`, `StoryCandidate`, `StoryArchitecture`, `ScriptDraft`, `SceneSpec`), versioned alongside prompts.
- **Schema fields describe intent, not mechanics:** the LLM does not emit durations or timestamps; `duration` is optional in `SceneSpec` precisely so code assigns it ([timeline-specification](../media/timeline-specification.md)).
- **Semantic validation after schema validation** (code): scene sequence contiguity, referenced characters exist in the character bible, narration length bounds, forbidden-content checks.
- Large outputs generated in pieces (per act, per scene batch) rather than one giant JSON.

## Failure modes

Truncated JSON at `max_tokens`; trailing commentary; schema-valid but nonsensical content; models echoing the schema itself. Mitigations: sized token budgets, semantic validation, escalation ([model-routing](model-routing.md)).

## Model role, input, prompt strategy, cost, quality

See [prompting-strategy](prompting-strategy.md), [context-management](context-management.md). Each retry costs a full extra call; every retry is a cost event ([ai-cost-strategy](ai-cost-strategy.md)). Output quality is evaluated beyond validity ([ai-quality-evaluation](ai-quality-evaluation.md)).

## Current vs future

Current: generic validate-and-retry. Future: native JSON modes, semantic validators, stage schemas, persisted attempt records ([retry-and-recovery](../workflows/retry-and-recovery.md)).
