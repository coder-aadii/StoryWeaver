# Context Management

> How inputs are assembled and bounded for each LLM call.

## Status

**Planned** — no context builder, token counter or budget logic exists. The only related code is transcript chunking.

## Current implementation

[`ingestion/chunking.py`](../../apps/api/app/ingestion/chunking.py) `chunk_segments(segments, max_chars=1200)` groups consecutive timed `TranscriptSegment`s into `(text, start, end)` chunks. `transcript_chunks` stores `text`, `start_seconds`, `end_seconds`, `token_count`, `embedding`. Nothing persists chunks yet ([transcript-pipeline](../domains/transcript-pipeline.md)). Character-based sizing is a placeholder; no tokenizer is used.

## Problem

A 30-minute transcript is ~4–5k words — fits many modern models, but a *channel* of transcripts does not, and small local models have short effective context. Quality drops long before the hard limit.

## Target Architecture

A **context builder** per stage returns a bounded, ordered set of blocks:

| Stage | Context |
| --- | --- |
| Source understanding | Whole transcript if it fits, otherwise map-reduce over chunks (summarise each, then merge) |
| Story candidates | Extracted facts/events/themes (not raw transcript) + user steering |
| Story architecture | Chosen candidate + supporting facts retrieved via [RAG](rag-strategy.md) |
| Script | Architecture + act-by-act facts; previous act's tail for continuity |
| Scene drafting | Script section + character/visual bible entries for characters present |
| Image prompts | One scene + bible entries; never the whole script |

Rules: count tokens (tokenizer per provider, estimate when unknown); reserve output budget; keep stable prefixes (system + bibles) first to enable provider caching; label blocks and treat source text as untrusted data; record exactly what was sent (hashes + ids) for reproducibility.

**Intermediate representations are the main tool:** facts, events and themes are extracted once, stored, and reused, so later stages never re-read the raw transcript ([ai-cost-strategy](ai-cost-strategy.md)).

## Failure modes

Silent truncation by the provider; lost-in-the-middle omissions; stale bible entries; context leaking across projects. Mitigate with explicit budgets, scoped retrieval by `project_id`/source ids, and validation that required facts are referenced.

## Model role, prompt, output, validation, retry, cost, quality

See [prompting-strategy](prompting-strategy.md), [structured-output](structured-output.md), [model-routing](model-routing.md). Quality of context selection is itself evaluated ([ai-quality-evaluation](ai-quality-evaluation.md)).

## Open questions

Chunk size in tokens vs characters; whether to store extracted facts as rows (new tables — Decision pending) or JSON on a source analysis record; summary caching keys.

## Current vs future

Current: char-based chunker only. Future: full builder with budgets and provenance.
