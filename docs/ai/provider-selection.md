# Provider Selection

> What providers StoryWeaver can talk to, how they are selected, and what is verified.

## Status

**Partially implemented** — adapters implemented; selection is configuration-only.

## Provider matrix (current)

| Provider key | Class / factory | Capabilities | Config | Verified |
| --- | --- | --- | --- | --- |
| `ollama` | `OllamaProvider` | LLM (`/api/chat`), embeddings (`/api/embed`), `is_reachable()` (`/api/tags`) | `OLLAMA_BASE_URL` (defaults to `http://localhost:11434`) | Request shape unit-tested with mocked HTTP; not run against Ollama (not installed on the dev machine) |
| `google` | `GoogleProvider` | LLM (`generateContent`), embeddings (`batchEmbedContents`); key sent in `x-goog-api-key` header | `GOOGLE_AI_API_KEY` | Untested |
| `openrouter` | `OpenAICompatibleProvider` | LLM (`/chat/completions`) | `OPENROUTER_API_KEY` | Untested |
| `grok` | `OpenAICompatibleProvider` (xAI base URL) | LLM | `GROK_API_KEY` | Untested |
| `claude` | `ClaudeCompatibleProvider` (`/v1/messages`) | LLM; works with Anthropic-compatible proxies | `ANTHROPIC_BASE_URL` + `ANTHROPIC_API_KEY` | Untested |

Embedding providers registered: `ollama`, `google` only. Others (e.g. DeepSeek) are not registered — "Planned — not implemented"; see [adding-a-provider](../development/adding-a-provider.md).

## Selection mechanics

- `DEFAULT_LLM_PROVIDER` picks the provider; unknown names raise `ProviderNotConfiguredError`.
- `is_configured()` means credentials/URL are present, **not** that the service is reachable. Ollama reports "configured" by default because a base URL has a default; `GET /api/v1/health/providers` adds `ollama_reachable` for the real check ([provider-endpoints](../api/provider-endpoints.md)).
- A missing optional provider never stops startup; failure occurs only when it is used.

## Selection criteria (guidance, not code)

Cost per token, context window, structured-output reliability, creative quality, latency, privacy (does source text leave the machine?), rate limits, availability offline. Weigh these per task in [model-routing](model-routing.md). Which concrete provider/model suits which task is **Decision pending** and should be answered with evaluation data ([ai-quality-evaluation](ai-quality-evaluation.md)), not preference.

## Local-first, not local-only

Local models (Ollama) are the default so the product runs at zero recurring cost and with source text kept on the machine; cloud providers are optional adapters used when quality justifies it. Provider names above are examples of the interchangeable adapters implemented, not permanent choices — DeepSeek and others can be added behind the same interface ([adding-a-provider](../development/adding-a-provider.md)). Non-LLM capabilities (embeddings, image, TTS, STT) select providers independently of the LLM.

## Model/provider role, input, prompts, output, validation, retry

Provider-agnostic; see [llm-strategy](llm-strategy.md), [structured-output](structured-output.md).

## Cost and quality considerations

See [ai-cost-strategy](ai-cost-strategy.md). Privacy: cloud providers receive transcript-derived text; see [provider-security](../security/provider-security.md).

## Current vs future

Current: manual selection through `.env`. Future: per-task routing with fallback ([model-routing](model-routing.md)). Architecture: [provider-architecture](../architecture/provider-architecture.md).
