# Provider Endpoint

> Reports which optional AI/media providers are configured or reachable, without exposing credentials.

## Status

**Implemented** (`GET /api/v1/health/providers`). Reports configuration; it does not validate that keys work.

## Response

```json
{
  "default_llm_provider": "ollama",
  "default_llm_model_set": false,
  "llm": {"ollama": true, "google": false, "openrouter": false, "grok": false, "claude": false},
  "ollama_reachable": false,
  "comfyui": {"configured": false, "reachable": false},
  "temporal_configured": false
}
```

- `llm.<name>` = `is_configured()`: key present (or base URL for Ollama / base URL **and** key for `claude`). **Ollama is `true` by default** because its URL defaults to `http://localhost:11434`; use `ollama_reachable` (2 s timeout GET `/api/tags`) for real availability.
- `default_llm_model_set` — whether `DEFAULT_LLM_MODEL` is non-empty; no model names are returned.
- `comfyui.reachable` — 2 s GET `/system_stats` if a URL is set.
- `temporal_configured` — whether `TEMPORAL_ADDRESS` is non-empty; Temporal is not used by the code.

The `llm.ollama` flag is therefore **not** evidence that Ollama is running or that a model is installed; only `ollama_reachable` is. The embedding provider (Ollama/Google) is configured separately via `EMBEDDING_PROVIDER` and is not reported here.

No secrets, URLs or key fragments are returned (asserted in `tests/test_health.py`). The web Settings page renders this payload.

## Limitations

Not shown: embedding provider, voice/TTS, transcription, per-task model routing. No authentication on the endpoint ([authentication](authentication.md)). Probing may add ~2 s latency per unreachable service.

Related: [architecture/provider-architecture](../architecture/provider-architecture.md) · [ai/provider-selection](../ai/provider-selection.md) · [security/provider-security](../security/provider-security.md)
