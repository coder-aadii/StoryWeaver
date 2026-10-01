# Embeddings and Vector Search

> How vectors are stored and queried, and what is not built yet.

## Status

**Partially implemented.** Column type, HNSW index, provider `embed()` adapters and chunking exist; a test proves cosine nearest-neighbour ordering. **Embedding generation, semantic search endpoints and RAG are Planned — not implemented.** The Source Library (P1) does write chunks for every ingested transcript, with `embedding` left NULL; its keyword search uses a separate generated `tsvector` column with a GIN index, not these vectors ([source library](../domains/source-library.md)).

## Storage (implemented)

`transcript_chunks.embedding vector(768)` (nullable) plus `embedding_model` (string) recording which model produced it. Index: HNSW, cosine ops, `m=16`, `ef_construction=64`. Query shape (used in `tests/test_models.py`):

```python
select(TranscriptChunk).order_by(TranscriptChunk.embedding.cosine_distance(vec)).limit(k)
```

## Dimension is fixed

`EMBEDDING_DIM = 768` is a constant in `models/domain.py` and is baked into the `vector(768)` column by the migration. `Settings.embedding_dimensions` (default 768, env `EMBEDDING_DIMENSIONS`) is an **independent, unchecked** value: changing it does not change the column, and nothing compares it with `EMBEDDING_DIM` or with what a provider returns at runtime (a unit test only checks that the two defaults agree), so a mismatched model fails at insert time ([KI-6](../reference/status.md#known-issues-and-limitations)). A model with a different output size requires a migration (and re-embedding). Mixed models in one column are unsafe — filter on `embedding_model` or re-embed ([ai/embeddings](../ai/embeddings.md)).

## Providers (implemented, untested)

`EmbeddingProvider.embed(texts, model=...)`: Ollama (`/api/embed`) and Google (`batchEmbedContents`). Selected by `EMBEDDING_PROVIDER` / `EMBEDDING_MODEL`; no default model name is hard-coded. Registry: `intelligence/registry.get_embeddings`.

## Chunking (implemented)

`chunk_segments` groups timed segments into ~1200-char chunks keeping `start`/`end`. Token counting and overlap: *Decision pending*.

## Target (Planned — not implemented)

```text
Transcript ready → chunk → batch embed → write chunks → searchable
Query → embed → cosine top-k (+ filters: collection, topic, project) → rerank? → answer/RAG
```
Use cases: find related sources, "have I already made a video on this?", unused ideas in a collection. Design in [ai/rag-strategy](../ai/rag-strategy.md) and [domains/research-and-intelligence](../domains/research-and-intelligence.md). Embeddings for ideas/scripts (not only transcripts) would need new storage — see [below](#originality-and-similarity-data-direction).

## Operational notes

HNSW build cost grows with row count; not an issue at current scale. `pgvector` must exist in the DB (`/api/v1/health/ready` checks it). See [health-and-readiness](../api/health-and-readiness.md).

## Originality and similarity data direction

**Status: Planned — not implemented; every storage choice here is Decision pending.** This section states the product/engineering goal and the data it implies. It makes no claim about copyright or legal standards, and no similarity threshold has been chosen.

**Goal.** Detect when a generated script (or story candidate) is *too close* to (a) its source material, (b) previously generated projects, or (c) previously used story ideas, so the user can regenerate or reframe before expensive downstream work. The product principle is *factual grounding with narrative originality*: the same facts may be reused, while structure, hook, pacing, framing, narration and scene order should differ ([domains/story-generation](../domains/story-generation.md)).

**What exists.** Only `transcript_chunks.embedding` (+ HNSW cosine index) for *source* text, tested for nearest-neighbour ordering. Nothing embeds scripts, candidates or ideas; no comparison code, no stored similarity result, no used-idea records ([KI-22](../reference/status.md#known-issues-and-limitations)).

**Data needed (Target).**

| Need | Direction |
| --- | --- |
| Vectors for generated text (script versions, story candidates/summaries, accepted ideas) | Either a generic `text_embeddings` table (`owner_type`, `owner_id`, `model`, `vector(768)`, `text_hash`) or an `embedding` column per artifact table. Generic table = one index, polymorphic owner without FK integrity; per-table column = integrity, more migrations |
| Comparable vectors | Comparisons are only meaningful between vectors from the **same embedding model** (and dimension); store `model` with every vector and filter on it ([ai/embeddings](../ai/embeddings.md)) |
| Comparison targets | (a) the project's source chunks (existing table), (b) other projects' script/candidate vectors, (c) accepted-idea vectors ("used ideas", see [source-data-model](source-data-model.md#source-usage-and-idea-reuse--storage-direction-decision-pending)) |
| Result records | A similarity result per check: subject (script version / candidate), compared-to reference, score, method (embedding cosine and/or deterministic lexical overlap computed by code), model, timestamp. Stored as a row in a `similarity_checks` table or as JSONB on the artifact — *Decision pending* |
| Thresholds | Not decided; likely per-project settings; scores are signals for a human gate, not guarantees |

**Division of labour.** Deterministic code computes vectors' distances and lexical overlap and stores results; an LLM may be asked to *explain* or suggest reframing, but must not be the sole judge ([ADR-004](../decisions/ADR-004-ai-vs-deterministic-responsibilities.md)). The result feeds the candidate-approval gate ([domains/project-system](../domains/project-system.md)). Evaluation of the check itself: [ai/ai-quality-evaluation](../ai/ai-quality-evaluation.md).
