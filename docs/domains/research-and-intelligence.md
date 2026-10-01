# Research and Intelligence

> Understanding sources and answering questions across the whole library.

## Status

**Planned — not implemented.** Only the supporting storage exists (chunk table with vector column + HNSW index, covered by a nearest-neighbour test) and the provider interfaces ([provider architecture](../architecture/provider-architecture.md)).

## Purpose

Convert stored transcripts into structured knowledge (facts, themes, entities, events) and semantic retrieval, so story generation starts from understanding instead of raw text.

## Problem being solved

Individual transcripts are long and unstructured. Users need to find related material across many sources, avoid repeating ideas, and ground stories in real facts.

## Inputs

Transcript chunks, metadata, user questions, project context.

## Outputs

Per-source analysis (summary, key facts with timestamps, themes, entities, event chains, topic labels) and ranked search results with citations.

## Entities

`TranscriptChunk.embedding`, `Topic`, `Collection`. A persisted analysis entity does not exist yet (Decision pending: dedicated table vs JSONB on `SourceVideo`); neither do used-idea/source-usage records or similarity records ([KI-22](../reference/status.md#known-issues-and-limitations)). Storage options for analysis results and story candidates are compared in the [story data model](../data/story-data-model.md); originality and similarity as a unit: [story generation](story-generation.md#originality-and-similarity).

## Workflow (Target Architecture)

1. Per-chunk embedding → pgvector.
2. Map-reduce analysis: chunk-level extraction → source-level synthesis (see [context management](../ai/context-management.md)).
3. Topic assignment ([topic system](topic-and-collection-system.md)).
4. Query-time retrieval: embed query → cosine search → (optional rerank) → cite chunks with timestamps ([RAG strategy](../ai/rag-strategy.md)).

Example questions to support: sources related to an idea; unused ideas in a collection; "have I already generated a video on this concept?"; facts across many transcripts.

## Business rules

- Every extracted fact must be traceable to chunk(s) and timestamps.
- Analysis stores prompt version + provider + model ([prompting strategy](../ai/prompting-strategy.md)).
- Retrieval never mixes embedding models.

## AI responsibilities

Extraction, summarization, theme/entity detection, classification, query embedding.

## Deterministic responsibilities

Chunking, vector search, filtering by collection/topic/date, citation assembly, caching, de-duplication.

## Current implementation

Vector column, HNSW cosine index, `EmbeddingProvider` interface with Ollama and Google adapters (mock-tested, never run against real services), `generate_structured` helper. No analysis or search endpoint.

## Planned implementation

See [roadmap](../product/feature-roadmap.md) phase 2–3.

## Edge cases

Sparse sources with few facts; contradictory sources; embedding model change (re-embed all); hallucinated facts (validate against chunks).

## Open questions

Reranking; hybrid keyword + vector search; analysis storage shape; evaluation set ([AI quality evaluation](../ai/ai-quality-evaluation.md)).
