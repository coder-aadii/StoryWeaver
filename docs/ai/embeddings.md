# Embeddings

> How text will be turned into vectors for semantic search.

## Status

**Partially implemented** — interface, two adapters and storage column exist; no workflow generates or stores embeddings.

## Current implementation

- Interface `EmbeddingProvider.embed(texts, *, model) -> list[list[float]]`.
- Adapters: `OllamaProvider` (`POST /api/embed`), `GoogleProvider` (`batchEmbedContents`). Registry: `get_embeddings()` using `EMBEDDING_PROVIDER` (default `ollama`) and `EMBEDDING_MODEL` (empty by default — you must choose one).
- Storage: `transcript_chunks.embedding vector(768)`; `embedding_model` string per chunk.
- Settings has `embedding_dimensions` (default 768), but the database dimension is the constant `EMBEDDING_DIM = 768` in [`models/domain.py`](../../apps/api/app/models/domain.py). **They are not linked at runtime** (the setting is read by no code); a unit test (`tests/test_config.py`) only fails if the two *defaults* diverge. Changing either alone gives inconsistent behaviour, and the schema needs an Alembic migration to change dimension.
- `embed()` checks the provider is configured and a model is set, wraps failures into the `ProviderError` family and verifies one vector per input, but no batching limits, retries or dimension checks are implemented: a vector whose length differs from 768 fails only at insert time ([KI-6](../reference/status.md#known-issues-and-limitations)). Google's embedding output size is configurable by model/request, and nothing here pins or verifies it.

## Target Architecture

1. Chunk transcript → 2. embed in batches via the registry → 3. verify returned length equals `EMBEDDING_DIM` (reject otherwise) → 4. store with `embedding_model` → 5. idempotent: skip chunks already embedded with the current model.

Model changes: store new vectors alongside old (e.g. new column/table) or re-embed fully; never mix models in one index. Decision pending on which.

## Model selection

Only models that emit exactly 768 dimensions work with the present schema; nothing checks this before insert. Choosing a model is configuration plus evaluation ([ai-quality-evaluation](ai-quality-evaluation.md)); local-first default is an Ollama embedding model. Multilingual support matters if sources are non-English — open question.

## Checklist (per the AI document contract)

| Item | Current | Target |
| --- | --- | --- |
| Model/provider role | Dedicated `EmbeddingProvider` (Ollama or Google), independent of the LLM | Same; model chosen by evaluation |
| Input context | None (nothing calls it) | Chunk text, optionally prefixed with the video title (Decision pending) |
| Prompt strategy | None — embeddings take no prompt | Same |
| Structured output | Float vector | Same, length-checked against `EMBEDDING_DIM` |
| Validation | None | Reject wrong length; reject NaN/empty |
| Retry/fallback | None | Retry on transient `ProviderError`; fall back to a second provider only if the dimension matches *and* the index is rebuilt consistently — generally avoid mixing models |
| Cost | Local ≈ free (CPU bound) | Embed lazily/in background; skip already-embedded chunks |
| Quality | Untested | Retrieval tests on a labelled query set ([rag-strategy](rag-strategy.md)) |

## Cost and quality

Local embedding is effectively free in money, bounded by CPU on a Ryzen 5 laptop; embed lazily/in the background, never at startup. See [ai-cost-strategy](ai-cost-strategy.md). Quality is evaluated by retrieval tests ([rag-strategy](rag-strategy.md)).

## Related

[embeddings-and-vector-search](../data/embeddings-and-vector-search.md) · [transcript-pipeline](../domains/transcript-pipeline.md) · [provider-selection](provider-selection.md).
