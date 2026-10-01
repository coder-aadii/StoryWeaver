# Provider Security

> Security rules for calls to LLM, embedding, image, voice and transcription providers, local or cloud.

## Status

Partially implemented. Isolation, timeouts and key handling exist; retries/backoff and egress controls do not.

## Principles

1. **Isolated:** only provider adapters perform provider HTTP. Business logic uses `generate`/`generate_structured`/`embed` ([provider architecture](../architecture/provider-architecture.md)). Every failure inside a provider call surfaces as a `ProviderError` subclass — `ProviderTimeoutError`, `ProviderResponseError` (empty, blocked, malformed or non-JSON replies) or plain `ProviderError` with a `status_code` — and an unset provider as `ProviderNotConfiguredError`; messages carry only the provider name, exception type and HTTP status, never URLs, headers or response bodies (previously KI-3, resolved in P0). This is verified with a shared mocked-HTTP contract suite, not against live services.
2. **Timeout-controlled:** adapter clients use a 120 s timeout (`http_client`); readiness probes use 2 s. Per-call timeout configuration: Planned.
3. **Validated:** model output is untrusted. `generate_structured` extracts JSON and validates it with the Pydantic schema; invalid output is retried once with the validation error, then fails. Never `eval`, never pass model output to a shell, SQL string or file path unvalidated.
4. **Retryable:** structured-output retry exists. Network retry with backoff, provider fallback chains and circuit breaking are Planned — not implemented ([retry and recovery](../workflows/retry-and-recovery.md)).
5. **Least data:** send only the context a task needs. Cloud providers receive source text — the user must decide per provider what may leave the machine ([local vs cloud](../ai/provider-selection.md)). Local-first default is Ollama.

## Prompt injection

Transcripts and other source material are **untrusted input**. They may contain text that tries to instruct the model. Rules: keep source text in clearly delimited data sections; keep system instructions separate; never give LLM calls tool or filesystem access based on source content; validate outputs against schemas; do not let generated text choose file paths, URLs or commands. Currently no prompts exist, so this is a design rule for the future pipeline ([prompting strategy](../ai/prompting-strategy.md), [threat model](threat-model.md)).

## Logging of provider calls

The `llm.generated` event logs `provider`, `model`, `duration`, `output_tokens` and `status`; log redaction masks secret-named keys and scrubs secret-shaped values in all strings, including the exception text the workflow runner logs (previously KI-2, resolved in P0). Redaction is best-effort, so a provider error that echoed a secret in an unusual format could still reach the logs. Adapters send keys in headers and never interpolate them into messages.

## Egress and configuration

`OLLAMA_BASE_URL`, `ANTHROPIC_BASE_URL`, `COMFYUI_BASE_URL` are operator-set and not allow-listed; the health endpoint will request them. Treat them as trusted configuration, never as request input. Third-party proxies (e.g. Claude-compatible gateways) see all prompts.

## Legal note

Nothing in StoryWeaver guarantees that generated content is original or copyright-safe; see [content policy](../product/content-policy-and-source-usage.md).
