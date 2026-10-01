# Adding a Provider

> How to add an LLM, embedding, image or voice provider without touching business logic.

## Status

Implemented (LLM/embedding registry). Image and voice have interfaces but **no registry** — `get_image_generator()` / `get_voice_provider()` are simple factories. See [Provider architecture](../architecture/provider-architecture.md).

## LLM provider

1. Create `apps/api/app/intelligence/providers/<name>.py` with a class extending `LLMProvider` (`providers/base.py`):
   - `name: str`
   - `is_configured() -> bool` (must not do network I/O)
   - `_complete(prompt, *, system, model, temperature, max_tokens) -> (text, input_tokens, output_tokens)`
   Do **not** override `generate`/`generate_structured`; the base class handles the not-configured check, timing, logging, `httpx.HTTPError` → `ProviderError`, and JSON validation with one retry.
2. OpenAI-style APIs: reuse `OpenAICompatibleProvider(name, base_url, api_key)` (how OpenRouter and Grok are done) via a small factory.
3. Add settings in `app/core/config.py` (e.g. `<name>_api_key`) and a placeholder in `.env.example`. Keys must stay server-side; send them in headers, never URLs.
4. Register in `intelligence/registry.py` `_LLM` (and `_EMBEDDING` if it implements `EmbeddingProvider.embed`). `llm_status()` then reports it automatically on `/health/providers`.
5. Tests with `httpx.MockTransport` (pattern in `tests/test_units.py::test_ollama_provider_http_shape`): assert request path/body shape and response parsing. No network in tests.

## Image / voice provider

Subclass `ImageGenerator` (`visual/base.py`) or `VoiceProvider` (`voice/base.py`), implement `is_configured` and `generate`/`synthesize`, and select it in the factory. Fail with `ProviderNotConfiguredError` rather than returning fake output. Voice durations must be **measured** from audio by code.

## Checklist

- [ ] Nothing connects or loads a model at import/startup.
- [ ] Missing config → `is_configured() == False`, app still boots.
- [ ] No secret in logs or health output.
- [ ] Model name comes from settings ([model routing](../ai/model-routing.md)).
- [ ] Doc updated: [provider selection](../ai/provider-selection.md), [status](../reference/status.md).

Note: the Google, Claude-compatible, OpenRouter and Grok adapters have not been exercised against real services.

> Working as an AI coding agent? Read [AI agent guide](ai-agent-guide.md) first.
