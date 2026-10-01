# Unit Testing

> Pure-logic tests that need no database or network.

## Status

Implemented.

## Covered (`apps/api/tests/test_units.py`, `test_health.py`)

Counts: [testing strategy](testing-strategy.md#layers).

- **Storage safety:** traversal keys (`../`, absolute, empty, NUL) rejected; `put` streams and returns correct size/sha256; filename sanitisation.
- **YouTube URL classification:** video/short/channel/playlist accepted; `file://`, foreign hosts, look-alike hosts (`youtube.com.evil.com`), bad ids, `javascript:` rejected.
- **Chunking:** timing preserved across chunks.
- **Timeline:** sort by sequence, contiguous starts, explicit duration honoured, estimate clamped to 7 s.
- **LLM base class:** structured output retries then succeeds; gives up with `ProviderError`; unconfigured provider raises `ProviderNotConfiguredError`; `extract_json` strips prose/fences; Ollama request shape via `httpx.MockTransport`.
- **Health without DB:** `/health` works with no database; `/health/providers` never leaks a key.

Web/video unit tests: [frontend testing](frontend-testing.md), [media testing](media-testing.md).

## Conventions

Plain functions, `pytest.mark.parametrize` for input tables, `tmp_path` for files. Keep them under a second in total.

## Not covered

Google/OpenRouter/Grok/Claude adapters' request shapes, `FasterWhisperTranscriber`, `YouTubeExtractor.extract/list_videos` (need optional deps/network), `LocalRunner`, `MockImageGenerator` output validity. Add tests when those gain consumers.
