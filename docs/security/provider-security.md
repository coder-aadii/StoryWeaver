# Provider Security

> Security rules for calls to LLM, embedding, image, voice and transcription providers, local or cloud.

## Status

Partially implemented. Isolation, timeouts and key handling exist; retries/backoff and egress controls do not.

## Principles

1. **Isolated:** only provider adapters perform provider HTTP. Business logic uses `generate`/`generate_structured`/`embed` ([provider architecture](../architecture/provider-architecture.md)). A transport or HTTP-status failure (`httpx.HTTPError`) surfaces as `ProviderError`, and an unset provider as `ProviderNotConfiguredError`; response bodies are not logged. **This wrapping is limited:** a malformed but HTTP-200 response (missing `choices`/`candidates`/`content`, e.g. a safety-blocked Google reply) raises an unwrapped `KeyError`/`IndexError`/`JSONDecodeError`, and `generate_structured` retries only validation errors, so such failures abort without retry ([KI-3](../reference/status.md#known-issues-and-limitations)). Callers must not assume every provider failure is a `ProviderError`.
2. **Timeout-controlled:** adapter clients use a 120 s timeout (`http_client`); readiness probes use 2 s. Per-call timeout configuration: Planned.
3. **Validated:** model output is untrusted. `generate_structured` extracts JSON and validates it with the Pydantic schema; invalid output is retried once with the validation error, then fails. Never `eval`, never pass model output to a shell, SQL string or file path unvalidated.
4. **Retryable:** structured-output retry exists. Network retry with backoff, provider fallback chains and circuit breaking are Planned — not implemented ([retry and recovery](../workflows/retry-and-recovery.md)).
5. **Least data:** send only the context a task needs. Cloud providers receive source text — the user must decide per provider what may leave the machine ([local vs cloud](../ai/provider-selection.md)). Local-first default is Ollama.

## Prompt injection

Transcripts and other source material are **untrusted input**. They may contain text that tries to instruct the model. Rules: keep source text in clearly delimited data sections; keep system instructions separate; never give LLM calls tool or filesystem access based on source content; validate outputs against schemas; do not let generated text choose file paths, URLs or commands. Currently no prompts exist, so this is a design rule for the future pipeline ([prompting strategy](../ai/prompting-strategy.md), [threat model](threat-model.md)).

## Logging of provider calls

The `llm.generated` event is redacted by key name, which masks `output_tokens` ([KI-2](../reference/status.md#known-issues-and-limitations)); and the workflow runner logs exception text unscrubbed ([KI-2](../reference/status.md#known-issues-and-limitations)), so a provider error message that echoed a secret would reach the logs. Adapters send keys in headers and never interpolate them into messages.

## Egress and configuration

`OLLAMA_BASE_URL`, `ANTHROPIC_BASE_URL`, `COMFYUI_BASE_URL` are operator-set and not allow-listed; the health endpoint will request them. Treat them as trusted configuration, never as request input. Third-party proxies (e.g. Claude-compatible gateways) see all prompts.

## Legal note

Nothing in StoryWeaver guarantees that generated content is original or copyright-safe; see [content policy](../product/content-policy-and-source-usage.md).
