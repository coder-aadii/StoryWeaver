# Unit Testing

> Pure-logic tests that need no database or network.

## Status

Implemented.

## Covered (`apps/api/tests/`: `test_units.py`, `test_health.py`, `test_config.py`, `test_logging.py`, `test_provider_contract.py`, `test_api_hardening.py` (schema/error-mapping parts), `test_db_safety.py`, `test_timeline_contract.py`)

Counts: [testing strategy](testing-strategy.md#layers).

- **Storage safety:** traversal keys (`../`, absolute, empty, NUL) rejected; `put` streams and returns correct size/sha256; filename sanitisation.
- **YouTube URL classification:** video/short/channel/playlist accepted; `file://`, foreign hosts, look-alike hosts (`youtube.com.evil.com`), bad ids, `javascript:` rejected.
- **Chunking:** timing preserved across chunks.
- **Timeline:** sort by sequence, contiguous starts, explicit duration honoured, estimate clamped to 7 s.
- **LLM base class:** structured output retries then succeeds (also after an empty/blocked reply); gives up with `ProviderResponseError`; unconfigured provider raises `ProviderNotConfiguredError`; `extract_json` strips prose/fences.
- **Provider contract suite (`test_provider_contract.py`):** every LLM adapter (Ollama, Google, OpenRouter, Grok, Claude-compatible) and both embedding adapters are exercised through `httpx.MockTransport` for request path/headers, success parse, HTTP 4xx/5xx (with `status_code`), timeouts, connection errors, malformed 200s and non-JSON replies, missing model, and that the secret never appears in the URL, exception text or logs. **Mocked HTTP only — not evidence that any adapter works against the live service.**
- **Config and logging:** empty `STORAGE_ROOT` means unset; redaction keeps `output_tokens` and masks secret keys/values (table-driven true/false-positive cases).
- **API validation and error mapping (no DB):** `null` on required PATCH fields, over-long values, URL validation on create, domain error → HTTP status/`code`, readiness failure typed and logged.
- **Test-database safety:** the `_test` name rule and the application-database rule (`db_safety.py`).
- **Python↔zod contract:** shared valid/invalid sample documents.
- **Health without DB:** `/health` works with no database; `/health/providers` never leaks a key.

Web/video unit tests: [frontend testing](frontend-testing.md), [media testing](media-testing.md).

## Conventions

Plain functions, `pytest.mark.parametrize` for input tables, `tmp_path` for files. Keep them under a second in total.

## Not covered

Live behavior of any provider adapter, `FasterWhisperTranscriber`, `YouTubeExtractor.extract/list_videos` (need optional deps/network), `LocalRunner`, `MockImageGenerator` output validity. Add tests when those gain consumers.
